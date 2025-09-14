// This file contains utility functions for formatting messages.

export const formatUserMessage = (message: string, accentColor: string): string => {
    return `<span style="color: ${accentColor};">${message}</span>`;
};

export const formatAIResponse = (response: string): string => {
    return `<div class="ai-response"><img src="/path/to/mia-icon.png" alt="Mia Icon" /> ${response}</div>`;
};

export const formatFeedback = (likes: number, dislikes: number): string => {
    return `Likes: ${likes}, Dislikes: ${dislikes}`;
};