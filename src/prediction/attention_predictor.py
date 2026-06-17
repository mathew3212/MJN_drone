"""
AttentionPredictor
==================
Learned attention-based trajectory predictor using scaled dot-product
cross-attention over obstacle history. Implements a multi-head attention
layer in pure NumPy with a PyTorch-compatible interface.

When PyTorch is available, automatically uses GPU-accelerated torch tensors.
Otherwise falls back to NumPy with equivalent semantics.

Architecture:
  Input:   (batch_size, seq_len, features)  -- obstacle position history
           features = [x, y, vx, vy, ax, ay]
  Encoder: 2-layer MLP -> key/value embeddings
  Attention: Scaled dot-product cross-attention (multi-head)
  Decoder: MLP -> predicted future positions with uncertainty
  Output:  (batch_size, pred_horizon, 4)  -- [x, y, confidence, variance]
"""

import numpy as np

try:
    import torch
    import torch.nn.functional as F

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class AttentionPredictor:
    """Learned multi-head attention trajectory predictor.

    Parameters
    ----------
    input_dim : int
        Number of input features per timestep (default 6: x, y, vx, vy, ax, ay).
    seq_len : int
        Number of historical timesteps to attend over (default 6).
    pred_horizon : int
        Number of future timesteps to predict (default 10).
    d_model : int
        Internal embedding dimension (default 64).
    n_heads : int
        Number of attention heads (default 4).
    dropout : float
        Dropout rate (default 0.1).
    use_torch : bool or None
        If None, auto-detect torch availability. Force True/False to override.
    """

    def __init__(
        self,
        input_dim: int = 6,
        seq_len: int = 6,
        pred_horizon: int = 10,
        d_model: int = 64,
        n_heads: int = 4,
        dropout: float = 0.1,
        use_torch: bool | None = None,
    ):
        self.input_dim = input_dim
        self.seq_len = seq_len
        self.pred_horizon = pred_horizon
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.dropout = dropout
        self.use_torch = HAS_TORCH if use_torch is None else use_torch

        # --- Learned weight matrices (NumPy backend) ---
        scale = d_model ** -0.5

        # Input projection
        self.W_in = np.random.randn(input_dim, d_model).astype(np.float32) * scale * 0.1

        # Q, K, V projections (combined for efficiency)
        self.W_q = np.random.randn(d_model, d_model).astype(np.float32) * scale * 0.1
        self.W_k = np.random.randn(d_model, d_model).astype(np.float32) * scale * 0.1
        self.W_v = np.random.randn(d_model, d_model).astype(np.float32) * scale * 0.1
        self.W_o = np.random.randn(d_model, d_model).astype(np.float32) * scale * 0.1

        # Positional encoding
        self.pos_encoding = self._create_positional_encoding(seq_len + pred_horizon, d_model)

        # Feed-forward network (MLP after attention)
        self.W_ff1 = np.random.randn(d_model, d_model * 4).astype(np.float32) * scale * 0.1
        self.b_ff1 = np.zeros(d_model * 4, dtype=np.float32)
        self.W_ff2 = np.random.randn(d_model * 4, d_model).astype(np.float32) * scale * 0.1
        self.b_ff2 = np.zeros(d_model, dtype=np.float32)

        # Output projection -> [x, y, confidence, variance]
        self.W_out = np.random.randn(d_model, 4).astype(np.float32) * scale * 0.1
        self.b_out = np.zeros(4, dtype=np.float32)

        # Layer norm parameters
        self.ln1_g = np.ones(d_model, dtype=np.float32)
        self.ln1_b = np.zeros(d_model, dtype=np.float32)
        self.ln2_g = np.ones(d_model, dtype=np.float32)
        self.ln2_b = np.zeros(d_model, dtype=np.float32)

        # Optimizer state (Adam)
        self._optim_state = {}

        # Training mode flag
        self.training = True

        # --- Torch parameters (if available) ---
        if self.use_torch:
            self._init_torch_params()

    def _create_positional_encoding(self, max_len: int, d_model: int) -> np.ndarray:
        """Sinusoidal positional encoding."""
        pe = np.zeros((max_len, d_model), dtype=np.float32)
        pos = np.arange(max_len)[:, None]
        div = np.exp(-np.arange(0, d_model, 2) * np.log(10000.0) / d_model)
        pe[:, 0::2] = np.sin(pos * div)
        pe[:, 1::2] = np.cos(pos * div)
        return pe

    def _init_torch_params(self):
        """Convert NumPy weights to torch tensors when available."""
        import torch

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        for name in ["W_in", "W_q", "W_k", "W_v", "W_o",
                      "W_ff1", "b_ff1", "W_ff2", "b_ff2",
                      "W_out", "b_out",
                      "ln1_g", "ln1_b", "ln2_g", "ln2_b"]:
            arr = getattr(self, name)
            setattr(self, f"_{name}_t", torch.from_numpy(arr).to(self._device))

    def _layer_norm(self, x: np.ndarray, g: np.ndarray, b: np.ndarray, eps: float = 1e-5) -> np.ndarray:
        """Layer normalization."""
        mean = x.mean(axis=-1, keepdims=True)
        var = x.var(axis=-1, keepdims=True)
        return g * (x - mean) / np.sqrt(var + eps) + b

    def _relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def _softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        """Numerically stable softmax."""
        x_max = x.max(axis=axis, keepdims=True)
        e_x = np.exp(x - x_max)
        return e_x / (e_x.sum(axis=axis, keepdims=True) + 1e-10)

    def _scaled_dot_product_attention(
        self, Q: np.ndarray, K: np.ndarray, V: np.ndarray, mask: np.ndarray | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Multi-head scaled dot-product attention.

        Parameters
        ----------
        Q, K, V : ndarray shape (batch, n_heads, seq_len, head_dim)
        mask : optional ndarray shape (batch, 1, 1, seq_len) or broadcastable

        Returns
        -------
        output : ndarray shape (batch, n_heads, seq_len, head_dim)
        attn_weights : ndarray shape (batch, n_heads, seq_len_q, seq_len_k)
        """
        d_k = Q.shape[-1]
        scores = np.matmul(Q, K.transpose(0, 1, 3, 2)) / (d_k ** 0.5)
        if mask is not None:
            scores = np.where(mask, scores, -1e9)
        attn = self._softmax(scores)
        if not self.training:
            attn = attn  # no dropout at inference
        output = np.matmul(attn, V)
        return output, attn

    def _split_heads(self, x: np.ndarray) -> np.ndarray:
        """Split last dim into (n_heads, head_dim)."""
        batch, seq, _ = x.shape
        return x.reshape(batch, seq, self.n_heads, self.head_dim).transpose(0, 2, 1, 3)

    def _merge_heads(self, x: np.ndarray) -> np.ndarray:
        """Merge (n_heads, head_dim) back to d_model."""
        batch, _, seq, _ = x.shape
        return x.transpose(0, 2, 1, 3).reshape(batch, seq, self.d_model)

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass through the attention predictor.

        Parameters
        ----------
        x : ndarray shape (batch_size, seq_len, input_dim)
            Input obstacle history features.

        Returns
        -------
        predictions : ndarray shape (batch_size, pred_horizon, 4)
            Predicted future [x, y, confidence, variance] for each step.
        """
        batch_size = x.shape[0]

        # --- Torch forward path ---
        if self.use_torch and HAS_TORCH:
            return self._forward_torch(x)

        # --- NumPy forward path ---
        # Input projection
        h = x @ self.W_in  # (batch, seq, d_model)

        # Add positional encoding
        h = h + self.pos_encoding[:self.seq_len][None, :, :]

        # Multi-head attention
        Q = self._split_heads(h @ self.W_q)  # (batch, n_heads, seq, head_dim)
        K = self._split_heads(h @ self.W_k)
        V = self._split_heads(h @ self.W_v)

        attn_out, attn_weights = self._scaled_dot_product_attention(Q, K, V)
        h_attn = self._merge_heads(attn_out) @ self.W_o

        # Residual + LayerNorm
        h = self._layer_norm(h + h_attn, self.ln1_g, self.ln1_b)

        # Feed-forward
        h_ff = h @ self.W_ff1 + self.b_ff1
        h_ff = self._relu(h_ff)
        h_ff = h_ff @ self.W_ff2 + self.b_ff2

        # Residual + LayerNorm
        h = self._layer_norm(h + h_ff, self.ln2_g, self.ln2_b)

        # Decode to predictions (use last timestep's representation)
        h_last = h[:, -1:, :]  # (batch, 1, d_model)

        # Expand to prediction horizon with learned positional conditioning
        pred_pos = self.pos_encoding[self.seq_len:self.seq_len + self.pred_horizon][None, :, :]
        h_pred = h_last + pred_pos

        # Output projection
        out = h_pred @ self.W_out + self.b_out  # (batch, pred_horizon, 4)

        # Ensure confidence in [0, 1] and variance > 0
        out[..., 2] = self._sigmoid(out[..., 2])  # confidence
        out[..., 3] = self._softplus(out[..., 3])  # variance

        # Store attention for analysis
        self._last_attention = attn_weights

        return out

    def _forward_torch(self, x: np.ndarray) -> np.ndarray:
        """Forward pass using PyTorch."""
        import torch

        xt = torch.from_numpy(x).to(self._device)
        with torch.no_grad() if not self.training else torch.set_grad_enabled(True):
            h = xt @ self._W_in_t
            h = h + torch.from_numpy(self.pos_encoding[:self.seq_len][None, :, :]).to(self._device)

            Q = self._split_heads_t(h @ self._W_q_t)
            K = self._split_heads_t(h @ self._W_k_t)
            V = self._split_heads_t(h @ self._W_v_t)

            d_k = Q.shape[-1]
            scores = torch.matmul(Q, K.transpose(-2, -1)) / (d_k ** 0.5)
            attn = torch.softmax(scores, dim=-1)
            attn_out = torch.matmul(attn, V)
            h_attn = self._merge_heads_t(attn_out) @ self._W_o_t

            # Layer norm
            h = self._layer_norm_t(h + h_attn, self._ln1_g_t, self._ln1_b_t)

            # FFN
            h_ff = torch.relu(h @ self._W_ff1_t + self._b_ff1_t)
            h_ff = h_ff @ self._W_ff2_t + self._b_ff2_t
            h = self._layer_norm_t(h + h_ff, self._ln2_g_t, self._ln2_b_t)

            h_last = h[:, -1:, :]
            pred_pos = torch.from_numpy(
                self.pos_encoding[self.seq_len:self.seq_len + self.pred_horizon][None, :, :]
            ).to(self._device)
            h_pred = h_last + pred_pos

            out = h_pred @ self._W_out_t + self._b_out_t
            out[..., 2] = torch.sigmoid(out[..., 2])
            out[..., 3] = torch.nn.functional.softplus(out[..., 3])

        return out.cpu().numpy()

    def _split_heads_t(self, x):
        """Torch split heads."""
        import torch
        batch, seq, _ = x.shape
        return x.reshape(batch, seq, self.n_heads, self.head_dim).transpose(1, 2)

    def _merge_heads_t(self, x):
        """Torch merge heads."""
        import torch
        batch, _, seq, _ = x.shape
        return x.transpose(1, 2).reshape(batch, seq, self.d_model)

    def _layer_norm_t(self, x, g, b, eps=1e-5):
        """Torch layer norm."""
        import torch
        mean = x.mean(dim=-1, keepdim=True)
        var = x.var(dim=-1, keepdim=True, unbiased=False)
        return g * (x - mean) / torch.sqrt(var + eps) + b

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))

    def _softplus(self, x: np.ndarray) -> np.ndarray:
        return np.log1p(np.exp(-np.abs(x))) + np.maximum(x, 0)

    def get_attention_weights(self) -> np.ndarray | None:
        """Return attention weights from last forward pass."""
        return getattr(self, "_last_attention", None)

    def predict_single(self, history: np.ndarray) -> np.ndarray:
        """Predict for a single obstacle's trajectory.

        Parameters
        ----------
        history : ndarray shape (seq_len, input_dim)

        Returns
        -------
        predictions : ndarray shape (pred_horizon, 4)
        """
        if history.ndim == 2:
            history = history[None, :, :]
        return self.forward(history)[0]

    def get_params(self) -> dict:
        """Get all learned parameters as numpy arrays (for serialization)."""
        params = {}
        for name in ["W_in", "W_q", "W_k", "W_v", "W_o",
                      "W_ff1", "b_ff1", "W_ff2", "b_ff2",
                      "W_out", "b_out",
                      "ln1_g", "ln1_b", "ln2_g", "ln2_b"]:
            params[name] = getattr(self, name).copy()
        return params

    def load_params(self, params: dict):
        """Load learned parameters from dictionary."""
        for name, arr in params.items():
            if hasattr(self, name):
                setattr(self, name, arr.astype(np.float32).copy())
        if self.use_torch:
            self._init_torch_params()