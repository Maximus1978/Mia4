// This file exports TypeScript types and interfaces used throughout the application.

export interface Session {
    id: string;
    title: string;
    createdAt: Date;
    updatedAt: Date;
}

export interface ProjectFolder {
    id: string;
    name: string;
    createdAt: Date;
}

export interface UserMessage {
    id: string;
    content: string;
    timestamp: Date;
}

export interface AIResponse {
    id: string;
    content: string;
    timestamp: Date;
}

export interface Feedback {
    messageId: string;
    liked: boolean;
}

export interface Config {
    accentColor: string;
    selectedModel: string;
}