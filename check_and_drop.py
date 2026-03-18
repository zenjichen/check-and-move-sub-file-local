"""
📂 Check & Drop SubFile
A modern GUI tool to extract (flatten) files from subfolders into a parent folder.
Built with CustomTkinter for a premium dark-themed experience.
"""

import os
import shutil
import threading
from pathlib import Path
from datetime import datetime

try:
    import customtkinter as ctk
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
    import customtkinter as ctk

from tkinter import filedialog, messagebox

# ──────────────────────────────────────────────
# Theme & Color Palette
# ──────────────────────────────────────────────
COLORS = {
    "bg_dark":       "#0f0f1a",
    "bg_card":       "#1a1a2e",
    "bg_card_hover": "#22223a",
    "bg_input":      "#16162b",
    "accent":        "#6c63ff",
    "accent_hover":  "#7f78ff",
    "accent_light":  "#a29bfe",
    "success":       "#00cec9",
    "warning":       "#fdcb6e",
    "danger":        "#ff6b6b",
    "text_primary":  "#e8e8f0",
    "text_secondary":"#9595b0",
    "text_muted":    "#5c5c7a",
    "border":        "#2d2d50",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ScrollableCheckboxFrame(ctk.CTkScrollableFrame):
    """A scrollable frame containing checkboxes for each subfolder."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.checkbox_vars: list[tuple[ctk.BooleanVar, str]] = []
        self.checkboxes: list[ctk.CTkCheckBox] = []

    def clear(self):
        for cb in self.checkboxes:
            cb.destroy()
        self.checkboxes.clear()
        self.checkbox_vars.clear()

    def add_item(self, folder_path: str, display_name: str):
        var = ctk.BooleanVar(value=False)
        cb = ctk.CTkCheckBox(
            self,
            text=f"  📁 {display_name}",
            variable=var,
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#ffffff",
            corner_radius=6,
        )
        cb.pack(anchor="w", padx=10, pady=4, fill="x")
        self.checkbox_vars.append((var, folder_path))
        self.checkboxes.append(cb)

    def select_all(self):
        for var, _ in self.checkbox_vars:
            var.set(True)

    def deselect_all(self):
        for var, _ in self.checkbox_vars:
            var.set(False)

    def get_selected(self) -> list[str]:
        return [path for var, path in self.checkbox_vars if var.get()]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ── Window Setup ──
        self.title("📂 Check & Drop SubFile")
        self.geometry("900x750")
        self.minsize(800, 650)
        self.configure(fg_color=COLORS["bg_dark"])

        self.source_path = ctk.StringVar(value="")
        self.dest_path = ctk.StringVar(value="")
        self.conflict_mode = ctk.StringVar(value="rename")
        self.transfer_mode = ctk.StringVar(value="move")
        self.delete_empty = ctk.BooleanVar(value=True)
        self.is_running = False
        self.operation_history: list[list[tuple[str, str, str]]] = []  # batches of (src, dest, mode)

        self._build_ui()

    # ════════════════════════════════════════════
    # UI Construction
    # ════════════════════════════════════════════
    def _build_ui(self):
        # ── Header ──
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_label = ctk.CTkLabel(
            header,
            text="📂  Check & Drop SubFile",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["accent_light"],
        )
        title_label.pack(side="left", padx=20)

        subtitle = ctk.CTkLabel(
            header,
            text="Flatten subfolders in one click",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        )
        subtitle.pack(side="left", padx=5)

        # ── Main Content ──
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=16, pady=(10, 0))
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)

        # ── Left Column ──
        left = ctk.CTkFrame(main, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._build_source_section(left)
        self._build_subfolder_section(left)

        # ── Right Column ──
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._build_settings_section(right)
        self._build_destination_section(right)

        # ── Bottom Section ──
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=(8, 0))
        self._build_action_section(bottom)

        # ── Log Section ──
        log_frame = ctk.CTkFrame(self, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, padx=16, pady=(4, 12))
        self._build_log_section(log_frame)

    def _build_source_section(self, parent):
        card = self._card(parent, "📁  Chọn Folder Mẹ (Source)")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))

        self.source_entry = ctk.CTkEntry(
            row,
            textvariable=self.source_path,
            placeholder_text="Chọn đường dẫn folder mẹ...",
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            height=38,
        )
        self.source_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ctk.CTkButton(
            row,
            text="📂 Browse",
            width=100,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=8,
            command=self._browse_source,
        )
        browse_btn.pack(side="left", padx=(0, 8))

        scan_btn = ctk.CTkButton(
            row,
            text="🔍 Quét",
            width=90,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#00b5b0",
            text_color="#0f0f1a",
            corner_radius=8,
            command=self._scan_subfolders,
        )
        scan_btn.pack(side="left")

    def _build_subfolder_section(self, parent):
        card = self._card(parent, "📋  Danh sách Folder Con")

        # Select / Deselect buttons
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 6))

        sel_all = ctk.CTkButton(
            btn_row,
            text="☑ Chọn tất cả",
            width=120,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=6,
            command=lambda: self.subfolder_list.select_all(),
        )
        sel_all.pack(side="left", padx=(0, 8))

        desel_all = ctk.CTkButton(
            btn_row,
            text="☐ Bỏ chọn tất cả",
            width=140,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["border"],
            hover_color=COLORS["text_muted"],
            corner_radius=6,
            command=lambda: self.subfolder_list.deselect_all(),
        )
        desel_all.pack(side="left", padx=(0, 8))

        refresh_btn = ctk.CTkButton(
            btn_row,
            text="🔄 Refresh",
            width=100,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["warning"],
            hover_color="#e5b85c",
            text_color="#0f0f1a",
            corner_radius=6,
            command=self._scan_subfolders,
        )
        refresh_btn.pack(side="left")

        self.folder_count_label = ctk.CTkLabel(
            btn_row,
            text="0 folder(s)",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        )
        self.folder_count_label.pack(side="right", padx=8)

        self.subfolder_list = ScrollableCheckboxFrame(
            card,
            fg_color=COLORS["bg_input"],
            corner_radius=8,
            height=200,
        )
        self.subfolder_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _build_settings_section(self, parent):
        card = self._card(parent, "⚙️  Cấu hình")

        # Transfer mode (Move / Copy)
        mode_label = ctk.CTkLabel(
            card,
            text="Chế độ chuyển file:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        mode_label.pack(anchor="w", padx=16, pady=(0, 6))

        mode_seg = ctk.CTkSegmentedButton(
            card,
            values=["move", "copy"],
            variable=self.transfer_mode,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["bg_input"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["border"],
            unselected_hover_color=COLORS["text_muted"],
            text_color="#ffffff",
            corner_radius=8,
        )
        mode_seg.pack(fill="x", padx=16, pady=(0, 6))

        mode_hint = ctk.CTkLabel(
            card,
            text="Move = cắt file  |  Copy = sao chép (giữ nguyên gốc)",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"],
        )
        mode_hint.pack(anchor="w", padx=16, pady=(0, 8))

        # Separator
        sep0 = ctk.CTkFrame(card, fg_color=COLORS["border"], height=1)
        sep0.pack(fill="x", padx=16, pady=(0, 10))

        # Conflict resolution
        conflict_label = ctk.CTkLabel(
            card,
            text="Xử lý trùng tên file:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        conflict_label.pack(anchor="w", padx=16, pady=(0, 6))

        options = [
            ("rename", "🔄 Tự động đổi tên  (an toàn)"),
            ("overwrite", "⚠️ Ghi đè  (overwrite)"),
            ("skip", "⏭️ Bỏ qua  (skip)"),
        ]
        for value, label in options:
            rb = ctk.CTkRadioButton(
                card,
                text=label,
                variable=self.conflict_mode,
                value=value,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"],
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                border_color=COLORS["border"],
            )
            rb.pack(anchor="w", padx=24, pady=3)

        # Separator
        sep = ctk.CTkFrame(card, fg_color=COLORS["border"], height=1)
        sep.pack(fill="x", padx=16, pady=12)

        # Extra options
        extra_label = ctk.CTkLabel(
            card,
            text="Tùy chọn thêm:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        extra_label.pack(anchor="w", padx=16, pady=(0, 6))

        del_cb = ctk.CTkCheckBox(
            card,
            text="  🗑️ Xóa folder con rỗng sau khi chuyển",
            variable=self.delete_empty,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            corner_radius=6,
        )
        del_cb.pack(anchor="w", padx=24, pady=(0, 12))

    def _build_destination_section(self, parent):
        card = self._card(parent, "📤  Folder Đích (Destination)")

        info = ctk.CTkLabel(
            card,
            text="Mặc định: cùng folder mẹ.\nHoặc chọn thư mục khác:",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            justify="left",
        )
        info.pack(anchor="w", padx=16, pady=(0, 6))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))

        self.dest_entry = ctk.CTkEntry(
            row,
            textvariable=self.dest_path,
            placeholder_text="(Mặc định = Folder Mẹ)",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            height=34,
        )
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        dest_btn = ctk.CTkButton(
            row,
            text="📂",
            width=40,
            height=34,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=8,
            command=self._browse_dest,
        )
        dest_btn.pack(side="left")

    def _build_action_section(self, parent):
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 6))
        btn_row.grid_columnconfigure(0, weight=1)

        self.start_btn = ctk.CTkButton(
            btn_row,
            text="🚀  BẮT ĐẦU CHUYỂN FILE",
            height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=10,
            command=self._start_extraction,
        )
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.undo_btn = ctk.CTkButton(
            btn_row,
            text="↩️ Hoàn tác",
            width=130,
            height=48,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["danger"],
            hover_color="#e05555",
            corner_radius=10,
            state="disabled",
            command=self._undo_last,
        )
        self.undo_btn.grid(row=0, column=1, sticky="e")

        self.progress = ctk.CTkProgressBar(
            parent,
            fg_color=COLORS["bg_card"],
            progress_color=COLORS["accent"],
            corner_radius=6,
            height=10,
        )
        self.progress.pack(fill="x")
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(
            parent,
            text="Sẵn sàng hoạt động ✨",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        )
        self.status_label.pack(anchor="w", pady=(4, 0))

    def _build_log_section(self, parent):
        log_header = ctk.CTkLabel(
            parent,
            text="📝 Log hoạt động",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_secondary"],
        )
        log_header.pack(anchor="w", pady=(0, 4))

        self.log_box = ctk.CTkTextbox(
            parent,
            fg_color=COLORS["bg_card"],
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8,
            border_color=COLORS["border"],
            border_width=1,
            height=120,
        )
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

    # ════════════════════════════════════════════
    # Helpers
    # ════════════════════════════════════════════
    def _card(self, parent, title: str) -> ctk.CTkFrame:
        """Create a styled card with a title label."""
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_color=COLORS["border"],
            border_width=1,
        )
        card.pack(fill="both", expand=True, pady=(0, 10))

        lbl = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["accent_light"],
        )
        lbl.pack(anchor="w", padx=16, pady=(12, 8))
        return card

    def _log(self, msg: str, tag: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"info": "ℹ️", "success": "✅", "warn": "⚠️", "error": "❌"}.get(tag, "")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{timestamp}] {prefix} {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ════════════════════════════════════════════
    # Browse Dialogs
    # ════════════════════════════════════════════
    def _browse_source(self):
        path = filedialog.askdirectory(title="Chọn Folder Mẹ")
        if path:
            self.source_path.set(path)
            self._log(f"Đã chọn folder mẹ: {path}")

    def _browse_dest(self):
        path = filedialog.askdirectory(title="Chọn Folder Đích")
        if path:
            self.dest_path.set(path)
            self._log(f"Đã chọn folder đích: {path}")

    # ════════════════════════════════════════════
    # Scan Subfolders
    # ════════════════════════════════════════════
    def _scan_subfolders(self):
        source = self.source_path.get().strip()
        if not source or not os.path.isdir(source):
            messagebox.showwarning("Lỗi", "Vui lòng chọn một folder mẹ hợp lệ trước!")
            return

        self.subfolder_list.clear()
        count = 0
        try:
            for entry in sorted(os.scandir(source), key=lambda e: e.name.lower()):
                if entry.is_dir():
                    self.subfolder_list.add_item(entry.path, entry.name)
                    count += 1
        except PermissionError:
            messagebox.showerror("Lỗi", "Không có quyền truy cập vào folder này!")
            return

        self.folder_count_label.configure(text=f"{count} folder(s)")
        if count == 0:
            self._log("Không tìm thấy folder con nào!", "warn")
        else:
            self._log(f"Quét xong: tìm thấy {count} folder con.", "success")

    # ════════════════════════════════════════════
    # Core Extraction Logic
    # ════════════════════════════════════════════
    def _start_extraction(self):
        if self.is_running:
            return

        selected = self.subfolder_list.get_selected()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn ít nhất 1 folder con để xử lý!")
            return

        source = self.source_path.get().strip()
        dest = self.dest_path.get().strip() or source

        if not os.path.isdir(dest):
            messagebox.showerror("Lỗi", f"Folder đích không tồn tại:\n{dest}")
            return

        # Confirm
        total_folders = len(selected)
        answer = messagebox.askyesno(
            "Xác nhận",
            f"Bạn đang chuẩn bị chuyển file từ {total_folders} folder con ra:\n{dest}\n\n"
            f"Xử lý trùng tên: {self.conflict_mode.get()}\n"
            f"Xóa folder rỗng: {'Có' if self.delete_empty.get() else 'Không'}\n\n"
            "Tiếp tục?",
        )
        if not answer:
            return

        self.is_running = True
        self.start_btn.configure(state="disabled", text="⏳  Đang xử lý...")
        self.progress.set(0)

        thread = threading.Thread(target=self._run_extraction, args=(selected, dest), daemon=True)
        thread.start()

    def _run_extraction(self, folders: list[str], dest: str):
        """Run the extraction in a background thread."""
        # 1. Collect all files
        all_files: list[tuple[str, str]] = []  # (full_path, relative_name_for_display)
        for folder in folders:
            for root, dirs, files in os.walk(folder):
                for f in files:
                    full = os.path.join(root, f)
                    all_files.append((full, f))

        total = len(all_files)
        if total == 0:
            self.after(0, lambda: self._log("Không có file nào để chuyển!", "warn"))
            self.after(0, self._reset_ui)
            return

        is_copy = self.transfer_mode.get() == "copy"
        action_label = "sao chép" if is_copy else "chuyển"
        self.after(0, lambda: self._log(f"Bắt đầu {action_label} {total} file...", "info"))
        moved = 0
        skipped = 0
        errors = 0

        current_batch: list[tuple[str, str, str]] = []  # history for this run

        for i, (file_path, file_name) in enumerate(all_files, 1):
            try:
                dest_file = os.path.join(dest, file_name)
                dest_file = self._resolve_conflict(file_path, dest_file)

                if dest_file is None:
                    skipped += 1
                    msg = f"Bỏ qua (đã tồn tại): {file_name}"
                    self.after(0, lambda m=msg: self._log(m, "warn"))
                else:
                    if is_copy:
                        shutil.copy2(file_path, dest_file)
                    else:
                        shutil.move(file_path, dest_file)
                    mode_tag = "copy" if is_copy else "move"
                    current_batch.append((file_path, dest_file, mode_tag))
                    moved += 1
                    final_name = os.path.basename(dest_file)
                    verb = "Đã sao chép" if is_copy else "Đã chuyển"
                    msg = f"{verb}: {final_name}"
                    self.after(0, lambda m=msg: self._log(m, "success"))
            except Exception as e:
                errors += 1
                msg = f"Lỗi khi chuyển {file_name}: {e}"
                self.after(0, lambda m=msg: self._log(m, "error"))

            # Update progress
            pct = i / total
            self.after(0, lambda p=pct, idx=i: self._update_progress(p, idx, total))

        # 2. Cleanup empty dirs
        if self.delete_empty.get():
            self.after(0, lambda: self._log("Đang dọn dẹp folder con rỗng...", "info"))
            for folder in folders:
                self._remove_empty_dirs(folder)

        # 3. Save history & Summary
        if current_batch:
            self.operation_history.append(current_batch)
            self.after(0, lambda: self.undo_btn.configure(state="normal"))

        summary = (
            f"✨ Hoàn tất! Đã chuyển: {moved} | Bỏ qua: {skipped} | Lỗi: {errors}"
        )
        self.after(0, lambda: self._log(summary, "success"))
        self.after(0, lambda: self.status_label.configure(text=summary))
        self.after(0, self._reset_ui)

    def _resolve_conflict(self, src: str, dest: str) -> str | None:
        """Handle file name conflicts based on user's chosen strategy."""
        if not os.path.exists(dest):
            return dest

        mode = self.conflict_mode.get()
        if mode == "overwrite":
            return dest
        if mode == "skip":
            return None
        # mode == "rename"
        base, ext = os.path.splitext(dest)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"

    def _remove_empty_dirs(self, path: str):
        """Recursively remove empty directories."""
        if not os.path.isdir(path):
            return
        for entry in os.scandir(path):
            if entry.is_dir():
                self._remove_empty_dirs(entry.path)
        # After cleaning children, check if this dir is now empty
        try:
            if not os.listdir(path):
                os.rmdir(path)
                msg = f"🗑️ Đã xóa folder rỗng: {os.path.basename(path)}"
                self.after(0, lambda m=msg: self._log(m, "info"))
        except Exception:
            pass

    def _update_progress(self, pct: float, current: int, total: int):
        self.progress.set(pct)
        self.status_label.configure(text=f"Đang xử lý: {current}/{total} file ({pct*100:.0f}%)")

    def _undo_last(self):
        """Undo the last batch of file operations."""
        if not self.operation_history:
            messagebox.showinfo("Thông báo", "Không có thao tác nào để hoàn tác!")
            return

        answer = messagebox.askyesno(
            "Xác nhận Hoàn tác",
            f"Bạn muốn hoàn tác lần thao tác gần nhất ({len(self.operation_history[-1])} file)?\n\n"
            "• Move → chuyển file về vị trí cũ\n"
            "• Copy → xóa bản sao đã tạo",
        )
        if not answer:
            return

        batch = self.operation_history.pop()
        restored = 0
        fail = 0
        self._log(f"Đang hoàn tác {len(batch)} thao tác...", "info")

        for src_original, dest_file, mode in reversed(batch):
            try:
                if mode == "move":
                    # Move back: ensure original parent dir exists
                    os.makedirs(os.path.dirname(src_original), exist_ok=True)
                    shutil.move(dest_file, src_original)
                    self._log(f"↩️ Đã chuyển về: {os.path.basename(src_original)}", "success")
                else:  # copy
                    if os.path.exists(dest_file):
                        os.remove(dest_file)
                    self._log(f"🗑️ Đã xóa bản sao: {os.path.basename(dest_file)}", "success")
                restored += 1
            except Exception as e:
                fail += 1
                self._log(f"Lỗi hoàn tác {os.path.basename(dest_file)}: {e}", "error")

        summary = f"↩️ Hoàn tác xong! Thành công: {restored} | Lỗi: {fail}"
        self._log(summary, "success")
        self.status_label.configure(text=summary)

        if not self.operation_history:
            self.undo_btn.configure(state="disabled")

    def _reset_ui(self):
        self.is_running = False
        self.start_btn.configure(state="normal", text="🚀  BẮT ĐẦU CHUYỂN FILE")


# ════════════════════════════════════════════
# Run
# ════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
