"use client";

import { motion } from "framer-motion";
import { Plus, Database, Activity, FileText, ChevronRight } from "lucide-react";
import styles from "./page.module.css";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  const handleCreateNew = () => {
    // Navigate to new workspace creation (dummy route for now)
    router.push("/workspace/new");
  };

  const handleOpenWorkspace = (id: string) => {
    router.push(`/workspace/${id}`);
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className="gradient-text">AI Financial Analyst</h1>
          <p className={styles.subtitle}>Không gian làm việc Multi-Project</p>
        </div>
      </header>

      <main className={styles.bentoGrid}>
        {/* Create New Block */}
        <motion.div
          className={`${styles.bentoCard} ${styles.cardCreate} glass-panel`}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleCreateNew}
        >
          <div className={styles.glowEffect}></div>
          <div className={styles.cardContent}>
            <div className={styles.iconWrapper}>
              <Plus size={32} />
            </div>
            <h2>Khởi tạo Phân tích Mới</h2>
            <p>Kéo thả PDF, BCTC, Excel hoặc CSV để bắt đầu nhúng dữ liệu vào AI.</p>
          </div>
        </motion.div>

        {/* ViFinQA Core Workspace Block */}
        <motion.div
          className={`${styles.bentoCard} ${styles.cardPrimary} glass-panel`}
          whileHover={{ scale: 1.02, y: -4 }}
          onClick={() => handleOpenWorkspace("vifinqa_core")}
        >
          <div className={styles.cardHeader}>
            <Database className={styles.accentIcon} />
            <ChevronRight className={styles.navIcon} />
          </div>
          <h3>Bộ Dữ liệu BCTC Mặc định</h3>
          <p>Hàng vạn báo cáo tài chính Việt Nam đã được xử lý (ViFinQA).</p>
          <div className={styles.stats}>
            <span className={styles.tag}>Dữ liệu hệ thống</span>
            <span className={styles.tag}>10.5K+ Bảng biểu</span>
          </div>
        </motion.div>

        {/* User Workspaces */}
        <motion.div
          className={`${styles.bentoCard} ${styles.cardSecondary} glass-panel`}
          whileHover={{ scale: 1.02, y: -4 }}
          onClick={() => handleOpenWorkspace("proj_sales24")}
        >
          <div className={styles.cardHeader}>
            <Activity className={styles.accentIcon2} />
            <ChevronRight className={styles.navIcon} />
          </div>
          <h3>Phân tích Sale 2024</h3>
          <p>Báo cáo doanh số bán lẻ quý 1 & 2.</p>
          <div className={styles.stats}>
            <span className={styles.tag}>Upload hôm qua</span>
            <span className={styles.tag}>3 Files</span>
          </div>
        </motion.div>

        <motion.div
          className={`${styles.bentoCard} ${styles.cardSecondary} glass-panel`}
          whileHover={{ scale: 1.02, y: -4 }}
          onClick={() => handleOpenWorkspace("proj_hpg")}
        >
          <div className={styles.cardHeader}>
            <FileText className={styles.accentIcon2} />
            <ChevronRight className={styles.navIcon} />
          </div>
          <h3>HPG - Báo cáo thường niên</h3>
          <p>Tập đoàn Hòa Phát 2021-2023.</p>
          <div className={styles.stats}>
            <span className={styles.tag}>2 tuần trước</span>
            <span className={styles.tag}>1 File PDF</span>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
