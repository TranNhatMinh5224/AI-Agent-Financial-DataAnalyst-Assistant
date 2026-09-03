import { useState, useCallback } from "react";
import { chatService } from "../services/api";

export interface AgentStepItem {
  agent: string;
  action: string;
  detail: string;
  success: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "ai";
  content: string;
  status?: string;
  steps?: AgentStepItem[];
}

export const useChatStream = (workspaceId: string) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "ai",
      content: "Xin chào! Tôi là AI Financial Analyst. Bạn muốn tôi phân tích điều gì từ kho dữ liệu hôm nay?",
    },
  ]);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = useCallback(async (text: string) => {
    // 1. Add User Message
    const userMsgId = Date.now().toString();
    setMessages((prev) => [...prev, { id: userMsgId, role: "user", content: text }]);

    // 2. Add empty AI Message
    const aiMsgId = (Date.now() + 1).toString();
    setMessages((prev) => [
      ...prev, 
      { id: aiMsgId, role: "ai", content: "", status: "Đang chuẩn bị phân tích...", steps: [] }
    ]);
    setIsStreaming(true);

    try {
      const response = await chatService.streamChat(text);

      if (!response.body) throw new Error("No body");
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      let currentEvent = "";
      let currentContent = "";
      let stepsList: AgentStepItem[] = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        
        const lines = chunk.split("\n");
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          if (trimmed.startsWith("event:")) {
            currentEvent = trimmed.replace("event:", "").trim();
          } else if (trimmed.startsWith("data:")) {
            const rawData = trimmed.slice(5).trim();
            if (rawData === "[DONE]") break;

            if (currentEvent === "status") {
              const statusText = rawData.replace(/^"|"$/g, "");
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === aiMsgId ? { ...msg, status: statusText } : msg
                )
              );
            } else if (currentEvent === "step") {
              try {
                const stepObj: AgentStepItem = JSON.parse(rawData);
                stepsList = [...stepsList, stepObj];
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === aiMsgId ? { ...msg, steps: stepsList } : msg
                  )
                );
              } catch (e) {
                // ignore json error
              }
            } else if (currentEvent === "message") {
              try {
                const msgObj = JSON.parse(rawData);
                currentContent += msgObj.text || "";
              } catch (e) {
                currentContent += rawData;
              }
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === aiMsgId ? { ...msg, content: currentContent, status: undefined } : msg
                )
              );
            }
          }
        }
      }
    } catch (error) {
      console.error("Lỗi SSE:", error);
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === aiMsgId ? { ...msg, content: "Lỗi kết nối tới Server." } : msg
        )
      );
    } finally {
      setIsStreaming(false);
    }
  }, [workspaceId]);

  return {
    messages,
    sendMessage,
    isStreaming,
    setMessages
  };
};
