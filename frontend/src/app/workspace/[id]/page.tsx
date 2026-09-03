"use client";

import { useState, useRef, useEffect } from "react";
import { useParams } from "next/navigation";
import styles from "./workspace.module.css";
import { Send, Paperclip, Loader2, FileUp, X, Brain, CheckCircle2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChatStream } from "@/hooks/useChatStream";

export default function WorkspacePage() {
  const routeParams = useParams();
  const workspaceId = (routeParams?.id as string) || "vifinqa_core";

  const { messages, sendMessage, isStreaming } = useChatStream(workspaceId);
  const [inputValue, setInputValue] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isStreaming) return;
    const text = inputValue;
    setInputValue("");
    await sendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className={styles.workspaceContainer}>
      {/* Header */}
      <header className={styles.header}>
        <div>
          <h2 className={styles.workspaceTitle}>Workspace: {workspaceId}</h2>
          <p className={styles.workspaceStatus}>
            <span className={styles.statusIndicator}></span>
            Database connected
          </p>
        </div>
        <button className={styles.uploadBtn} onClick={() => setShowUploadModal(true)}>
          <FileUp size={18} />
          <span>Tải tài liệu lên</span>
        </button>
      </header>

      {/* Chat Area */}
      <div className={styles.chatArea}>
        <div className={styles.messageList}>
          {messages.map((msg) => (
            <motion.div 
              key={msg.id} 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`${styles.messageWrapper} ${msg.role === 'user' ? styles.wrapperUser : styles.wrapperAi}`}
            >
              <div className={`${styles.messageBubble} ${msg.role === 'user' ? styles.bubbleUser : styles.bubbleAi}`}>
                {/* 1. Quá trình suy luận của Đa Agent (CLER) */}
                {msg.role === 'ai' && msg.steps && msg.steps.length > 0 && (
                  <div className={styles.reasoningBox}>
                    <div className={styles.reasoningHeader}>
                      <Brain size={16} className={styles.reasoningIcon} />
                      <span>Quá trình suy luận Đa Agent (CLER)</span>
                    </div>
                    <div className={styles.stepsList}>
                      {msg.steps.map((st, sIdx) => (
                        <div key={sIdx} className={styles.stepItem}>
                          <span className={`${styles.agentBadge} ${styles['badge_' + st.agent.toLowerCase()] || ''}`}>
                            {st.agent}
                          </span>
                          <span className={styles.stepAction}>{st.action}:</span>
                          <span className={styles.stepDetail} title={st.detail}>{st.detail}</span>
                          <CheckCircle2 size={13} className={styles.stepCheck} />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 2. Trạng thái Loading lúc đang suy luận */}
                {msg.role === 'ai' && msg.status && !msg.content && (
                  <div className={styles.streamingStatus}>
                    <Loader2 size={16} className={styles.spinner} />
                    <span>{msg.status}</span>
                  </div>
                )}

                {/* 3. Nội dung câu trả lời chuẩn Markdown */}
                {msg.content && (
                  <div className={styles.markdownContent}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className={styles.inputContainer}>
          <div className={styles.inputBox}>
            <button className={styles.attachBtn}>
              <Paperclip size={20} />
            </button>
            <textarea 
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Nhập câu hỏi tài chính..."
              className={styles.textarea}
              rows={1}
            />
            <button 
              className={`${styles.sendBtn} ${inputValue.trim() && !isStreaming ? styles.sendBtnActive : ''}`}
              onClick={handleSendMessage}
              disabled={isStreaming}
            >
              {isStreaming ? <Loader2 size={18} className={styles.spinner} /> : <Send size={18} />}
            </button>
          </div>
          <p className={styles.inputDisclaimer}>
            AI có thể mắc sai lầm. Hãy luôn đối chiếu số liệu với BCTC gốc.
          </p>
        </div>
      </div>

      {/* Upload Modal (Glassmorphism) */}
      <AnimatePresence>
        {showUploadModal && (
          <motion.div 
            className={styles.modalOverlay}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div 
              className={styles.uploadModal}
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
            >
              <button className={styles.closeBtn} onClick={() => setShowUploadModal(false)}>
                <X size={20} />
              </button>
              
              <h3>Tải lên Tài liệu Tài chính</h3>
              <p>Hỗ trợ định dạng PDF, Excel, Hình ảnh (hỗ trợ OCR tự động).</p>
              
              <div className={styles.dropZone}>
                <FileUp size={48} className={styles.dropIcon} />
                <p>Kéo thả file vào đây hoặc <span>Duyệt file</span></p>
              </div>

              {isUploading && (
                <div className={styles.uploadingState}>
                  <Loader2 className={styles.spinner} size={24} />
                  <span>Đang tải lên và xử lý OCR...</span>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
