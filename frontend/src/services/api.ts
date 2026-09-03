// Centralized API configuration and services

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

/**
 * Service to handle SSE Streaming for Chat
 */
export const chatService = {
  streamChat: async (message: string): Promise<Response> => {
    return await fetch(`${API_BASE_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
  }
};
