"use client";

import { ReactNode } from "react";
import styles from "./layout.module.css";
import { FolderGit2, Plus, MessageSquare, Settings, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  const router = useRouter();

  return (
    <div className={styles.layout}>
      {/* Sidebar Navigation */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logo} onClick={() => router.push("/")} style={{cursor: "pointer"}}>
            <FolderGit2 size={24} className={styles.logoIcon} />
            <h2>ViFinQA</h2>
          </div>
        </div>

        <button className={styles.newChatBtn} onClick={() => router.push("/workspace/new")}>
          <Plus size={18} />
          <span>Phiên làm việc mới</span>
        </button>

        <div className={styles.historyList}>
          <p className={styles.sectionTitle}>Lịch sử hôm nay</p>
          <div className={`${styles.historyItem} ${styles.active}`}>
            <MessageSquare size={16} />
            <span>Phân tích HPG Q2/2024</span>
          </div>
          <div className={styles.historyItem}>
            <MessageSquare size={16} />
            <span>Đánh giá rủi ro BCTC</span>
          </div>
        </div>

        <div className={styles.sidebarFooter}>
          <div className={styles.footerItem}>
            <Settings size={18} />
            <span>Cài đặt AI</span>
          </div>
          <div className={styles.footerItem}>
            <LogOut size={18} />
            <span>Đóng không gian</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className={styles.mainContent}>
        {children}
      </main>
    </div>
  );
}
