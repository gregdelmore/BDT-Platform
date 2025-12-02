export class WebSocketService {
    private ws: WebSocket | null = null;
    
    connect(url: string) {
        this.ws = new WebSocket(url);
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}