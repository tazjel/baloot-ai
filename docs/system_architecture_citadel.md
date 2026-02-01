# Baloot AI System Architecture (Citadel)

Generated using `senior-architect` skill guidelines.

```mermaid
graph TB
    subgraph Client ["Frontend (Citadel UI)"]
        UI[React App]
        SioClient[Socket.IO Client]
        ProfOverlay[Professor Overlay]
        Vision[Visionary Studio]
        
        UI --> SioClient
        UI --> ProfOverlay
        UI --> Vision
    end

    subgraph Infrastructure ["Infrastructure Layer"]
        LB[Load Balancer / Nginx]
        Redis[(Redis Store)]
        RedisPubSub{Redis Pub/Sub}
    end

    subgraph Backend ["Game Server (Python)"]
        SioServer[Socket.IO Server]
        Auth[Auth Handler]
        RoomMgr[Room Manager (Stateless)]
        GameLogic[Game Engine (Baloot)]
        
        SioServer --> Auth
        SioServer --> RoomMgr
        RoomMgr --> Redis
        RoomMgr --> GameLogic
    end

    subgraph AI ["AI Worker (The Brain)"]
        BotAgent[Bot Agent]
        MCTS[MCTS Engine]
        Memory[Memory Hall (Vector DB)]
        ProfAI[Professor AI]
        
        BotAgent --> Redis
        BotAgent --> MCTS
        ProfAI --> GameLogic
        ProfAI --> Memory
    end

    %% Connections
    SioClient -- "WebSockets" --> LB
    LB --> SioServer
    
    %% Redis Interactions
    RoomMgr -- "Save/Load State" --> Redis
    SioServer -- "Events" --> RedisPubSub
    BotAgent -- "Read State" --> Redis
    
    %% AI Flow
    BotAgent -- "Decisions" --> SioServer
    Vision -- "Training Data" --> AI
```

## Key Components
1.  **Stateless API**: The `RoomManager` relies entirely on Redis for state, allowing horizontal scaling.
2.  **AI Decoupling**: The AI Worker reads state directly from Redis or receives updates via `game_update` events, minimizing load on the socket server logic.
3.  **Visionary Studio**: A specialized module in the frontend for computer vision training (YOLOv8), feeding data back into the AI pipeline.
