"""
Simulation Exporter
===================
Real-time WebSocket server that exports drone state from the simulator.
Broadcasts DroneEntity (simulation input) to all connected GCS clients.

Note: Uses threading for async server to avoid blocking the sync simulator loop.
"""

import json
import logging
import threading
from typing import Optional, Dict, Any
from queue import Queue

try:
    import websockets
    import asyncio
except ImportError:
    websockets = None
    asyncio = None

from src.telemetry.gps_converter import GPSConverter

logger = logging.getLogger(__name__)


class SimulationExporter:
    """
    WebSocket server that broadcasts real-time drone state.
    
    Runs in a background thread to avoid blocking the simulator.
    Every simulation tick:
    1. Exporter.update(drone, world, ...) is called (sync)
    2. State is queued for broadcast
    3. Background thread sends to all connected clients
    
    Frontend receives via WebSocket and pipes to SimulationBridge.update()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        enabled: bool = True
    ):
        self.host = host
        self.port = port
        self.enabled = enabled and websockets is not None and asyncio is not None
        
        if not self.enabled:
            logger.warning("SimulationExporter: disabled (websockets/asyncio not available)")
            return
        
        self.clients: set = set()
        self.running = False
        self.tick_count = 0
        self.queue: Queue = Queue(maxsize=100)
        
        # Start background thread
        self.thread = threading.Thread(target=self._server_thread, daemon=True)
        self.thread.start()
        
    def _server_thread(self):
        """Background thread that runs the async WebSocket server."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._run_server(loop))
        except Exception as e:
            logger.error(f"Server thread error: {e}")
        finally:
            self.running = False

    async def _run_server(self, loop):
        """Run the WebSocket server in the background thread."""
        try:
            async def handler(websocket, path):
                self.clients.add(websocket)
                logger.info(f"GCS connected from {websocket.remote_address}. Total: {len(self.clients)}")
                try:
                    async for message in websocket:
                        if message == "ping":
                            await websocket.send("pong")
                except websockets.exceptions.ConnectionClosed:
                    pass
                finally:
                    self.clients.discard(websocket)
                    logger.info(f"GCS disconnected. Total: {len(self.clients)}")

            server = await websockets.serve(
                handler,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10,
            )
            self.running = True
            logger.info(f"📡 SimulationExporter listening on ws://{self.host}:{self.port}")
            
            # Process queue and broadcast
            while self.running:
                try:
                    # Check queue
                    while not self.queue.empty():
                        state = self.queue.get_nowait()
                        json_data = json.dumps(state)
                        
                        # Send to all clients
                        disconnected = set()
                        for client in self.clients:
                            try:
                                await client.send(json_data)
                            except Exception:
                                disconnected.add(client)
                        
                        self.clients -= disconnected
                    
                    await asyncio.sleep(0.01)  # 100Hz broadcast check
                except Exception as e:
                    logger.debug(f"Broadcast error: {e}")
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            if server:
                server.close()
                await server.wait_closed()

    def update(
        self,
        drone,
        world,
        battery_percentage: float = 100.0,
        battery_voltage: float = 22.4,
        battery_current: float = 0.0,
        battery_temperature: float = 25.0,
        signal_strength: float = 95.0,
        gps_satellites: int = 12,
        gps_hdop: float = 0.8,
        gps_accuracy: float = 1.0,
        flight_mode: str = "NORMAL",
        status: str = "ARMED",
    ):
        """
        Queue drone state for broadcast (non-blocking).
        
        Called every simulation tick from the main loop.
        Queues state for async broadcast in background thread.
        """
        if not self.enabled:
            return
        
        try:
            # Convert local coordinates to GPS
            latitude, longitude, altitude = GPSConverter.local_to_gps(
                drone.x,
                drone.y,
                0.0  # No altitude offset for now
            )
            
            # Get heading in degrees (convert from radians if needed)
            heading = drone.heading
            if isinstance(heading, float):
                heading = (heading * 180 / 3.14159) % 360
            
            # Build SimulationInput format
            state = {
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude,
                "heading": heading,
                "pitch": 0.0,  # Not available in simple simulator
                "roll": 0.0,   # Not available in simple simulator
                "yaw": heading,
                "velocity": drone.velocity_magnitude if hasattr(drone, 'velocity_magnitude') else 0.0,
                "verticalSpeed": 0.0,  # Not available
                "battery_percentage": battery_percentage,
                "battery_voltage": battery_voltage,
                "battery_current": battery_current,
                "battery_temperature": battery_temperature,
                "signal_strength": signal_strength,
                "gps_satellites": gps_satellites,
                "gps_hdop": gps_hdop,
                "gps_accuracy": gps_accuracy,
                "status": status,
                "flight_mode": flight_mode,
                "timestamp": int(threading.active_count() * 1000),  # Use a simple counter
            }
            
            # Queue for broadcast (non-blocking)
            if not self.queue.full():
                self.queue.put_nowait(state)
            
            self.tick_count += 1
        except Exception as e:
            logger.debug(f"Update error: {e}")

    def is_connected(self) -> bool:
        """Check if any clients are connected."""
        return len(self.clients) > 0

    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.clients)

    def set_enabled(self, enabled: bool):
        """Enable/disable the exporter."""
        self.enabled = enabled
