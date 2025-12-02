'''WebSocket endpoint for real-time communication'''
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        logger.info(f"Client {client_id} disconnected")
    
    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    '''WebSocket endpoint handler'''
    if not client_id:
        client_id = str(uuid.uuid4())
    
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "subscribe":
                topic = message.get("topic")
                if topic not in manager.subscriptions:
                    manager.subscriptions[topic] = set()
                manager.subscriptions[topic].add(client_id)
                
            elif message.get("type") == "ping":
                await manager.send_personal_message(json.dumps({"type": "pong"}), client_id)
                
            else:
                # Echo back to sender
                await manager.send_personal_message(data, client_id)
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
