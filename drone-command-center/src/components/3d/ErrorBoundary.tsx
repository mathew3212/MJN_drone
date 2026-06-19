'use client';

import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ThreeErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[3D Map Error]', error.message, error.stack);
    if (this.props.onError) {
      this.props.onError(error, info);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-[#080810] text-white p-6">
          <div className="text-[#FF4D5A] text-lg font-mono mb-2">⚠ 3D ENGINE ERROR</div>
          <div className="text-[#6B7FA0] text-xs font-mono mb-4 max-w-md text-center">
            {this.state.error?.message || 'Unknown error initializing 3D scene'}
          </div>
          <button
            onClick={this.handleRetry}
            className="px-4 py-2 text-xs font-mono bg-[rgba(0,212,255,0.1)] border border-[rgba(0,212,255,0.3)] text-[#00D4FF] rounded-lg hover:bg-[rgba(0,212,255,0.2)] transition-all"
          >
            RETRY
          </button>
          <div className="mt-4 text-[#4A5A78] text-[9px] font-mono">
            MJN-3D-ENGINE v1.0 — Fallback Mode
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export class SuspenseFallback extends Component {
  render() {
    return (
      <div className="w-full h-full flex items-center justify-center bg-[#080810]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-[rgba(0,212,255,0.3)] border-t-[#00D4FF] rounded-full animate-spin" />
          <span className="text-[10px] font-mono text-[#4A5A78] tracking-wider uppercase">
            Initializing 3D Engine
          </span>
        </div>
      </div>
    );
  }
}