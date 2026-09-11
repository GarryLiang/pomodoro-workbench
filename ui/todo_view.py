"""待办页：任务清单的新增、编辑、完成与删除。"""

import re
import tkinter as tk
from tkinter import ttk, messagebox

from app.todo import (
    PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_NAMES,
    FILTER_ALL, FILTER_ACTIVE, FILTER_DONE,
)
from . import theme
from .widgets import make_card, card_title, card_muted

PRIORITY_OPTIONS = [("高", PRIORITY_HIGH), ("中", PRIORITY_MEDIUM),
                    ("低", PRIORITY_LOW)]
PRIORITY_TEXT = dict(PRIORITY_OPTIONS)

STATUS_FILTERS = [("全部", FILTER_ALL), ("进行中", FILTER_ACTIVE),
                  ("已完成", FILTER_DONE)]

_COLS = ("state", "priority", "title", "due", "pomodoros", "created")

_DUE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class TodoView(ttk.Frame):
    """待办清单页面。"""

    def __init__(self, master, context):
        super().__init__(master)
        self.context = context
        self.manager = context.todo
        self._editing_id = None
        self._iids = {}
        self._build()
        self.refresh()

    # ================================================================ 构建界面
    def _build(self):
        self.configure(style="TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        editor = make_card(self)
        editor.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        editor.columnconfigure(1, weight=1)
        editor.columnconfigure(3, weight=1)

        head = tk.Frame(editor, bg=theme.CARD_BG)
        head.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        card_title(head, "待办清单").pack(side="left")
        self.hint = card_muted(head, "双击行可快速完成 / 恢复")
        self.hint.pack(side="right")

        tk.Label(editor, text="内容 *", bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                 font=theme.FONT_BODY).grid(row=1, column=0, sticky="w")
        self.entry_title = ttk.Entry(editor)
        self.entry_title.grid(row=1, column=1, sticky="ew", padx=(6, 12), pady=3)
        self.entry_title.bind("<Return>", lambda _e: self._on_save())

        tk.Label(editor, text="优先级", bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                 font=theme.FONT_BODY).grid(row=1, column=2, sticky="w")
        self.combo_priority = ttk.Combobox(editor, state="readonly", width=6,
                                           values=[t for t, _ in PRIORITY_OPTIONS])
        self.combo_priority.set("中")
        self.combo_priority.grid(row=1, column=3, sticky="w", padx=(6, 0), pady=3)

        tk.Label(editor, text="截止日期", bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                 font=theme.FONT_BODY).grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.entry_due = ttk.Entry(editor, width=14)
        self.entry_due.grid(row=2, column=1, sticky="w", padx=(6, 12), pady=(4, 0))

        tk.Label(editor, text="备注", bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                 font=theme.FONT_BODY).grid(row=2, column=2, sticky="w", pady=(4, 0))
        self.entry_note = ttk.Entry(editor)
        self.entry_note.grid(row=2, column=3, sticky="ew", padx=(6, 0), pady=(4, 0))

        actions = tk.Frame(editor, bg=theme.CARD_BG)
        actions.grid(row=3, column=0, columnspan=4, sticky="e", pady=(10, 0))
        self.btn_save = ttk.Button(actions, text="＋ 添加", style="Accent.TButton",
                                   command=self._on_save)
        self.btn_save.pack(side="right", padx=4)
        self.btn_cancel_edit = ttk.Button(actions, text="取消修改",
                                          style="Ghost.TButton",
                                          command=self._cancel_edit)
        self.btn_cancel_edit.pack(side="right", padx=4)
        self.btn_cancel_edit.state(["disabled"])

        # 列表卡
        table_card = make_card(self)
        table_card.grid(row=1, column=0, sticky="nsew")
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(1, weight=1)

        filter_bar = tk.Frame(table_card, bg=theme.CARD_BG)
        filter_bar.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        tk.Label(filter_bar, text="状态", bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                 font=theme.FONT_BODY).pack(side="left", padx=(0, 6))
        self.combo_status = ttk.Combobox(filter_bar, state="readonly", width=8,
                                         values=[t for t, _ in STATUS_FILTERS])
        self.combo_status.set("全部")
        self.combo_status.pack(side="left")
        self.combo_status.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        tk.Label(filter_bar, text="优先级", bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                 font=theme.FONT_BODY).pack(side="left", padx=(16, 6))
        self.combo_priority_filter = ttk.Combobox(
            filter_bar, state="readonly", width=6,
            values=["全部"] + [t for t, _ in PRIORITY_OPTIONS])
        self.combo_priority_filter.set("全部")
        self.combo_priority_filter.pack(side="left")
        self.combo_priority_filter.bind("<<ComboboxSelected>>",
                                        lambda _e: self.refresh())

        self.summary_label = tk.Label(filter_bar, text="", bg=theme.CARD_BG,
                                      fg=theme.TEXT_MUTED, font=theme.FONT_SMALL)
        self.summary_label.pack(side="right")

        wrap = tk.Frame(table_card, bg=theme.CARD_BG)
        wrap.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        wrap.columnconfigure(0, weight=1)
        wrap.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(wrap, columns=_COLS, show="headings",
                                 selectmode="browse")
        self.tree.heading("state", text="完成")
        self.tree.heading("priority", text="优先级")
        self.tree.heading("title", text="标题")
        self.tree.heading("due", text="截止日期")
        self.tree.heading("pomodoros", text="番茄")
        self.tree.heading("created", text="创建时间")
        self.tree.column("state", width=64, anchor="center", stretch=False)
        self.tree.column("priority", width=70, anchor="center", stretch=False)
        self.tree.column("title", width=300, anchor="w")
        self.tree.column("due", width=110, anchor="center", stretch=False)
        self.tree.column("pomodoros", width=60, anchor="center", stretch=False)
        self.tree.column("created", width=150, anchor="center", stretch=False)
        self.tree.tag_configure("p_high", foreground=theme.RED)
        self.tree.tag_configure("p_medium", foreground=theme.YELLOW)
        self.tree.tag_configure("p_low", foreground=theme.TEXT_MUTED)
        self.tree.tag_configure("done", foreground=theme.TEXT_MUTED)
        self.tree.tag_configure("overdue", foreground=theme.RED)
        self.tree.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(wrap, orient="vertical",
                               command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)

        # 行操作按钮
        op_bar = tk.Frame(table_card, bg=theme.CARD_BG)
        op_bar.grid(row=2, column=0, sticky="w", padx=6, pady=(0, 8))
        self.btn_toggle = ttk.Button(op_bar, text="完成所选", style="Ghost.TButton",
                                     command=self._on_toggle_done)
        self.btn_toggle.pack(side="left", padx=4)
        self.btn_edit = ttk.Button(op_bar, text="编辑所选", style="Ghost.TButton",
                                   command=self._on_edit)
        self.btn_edit.pack(side="left", padx=4)
        self.btn_delete = ttk.Button(op_bar, text="删除所选", style="Ghost.TButton",
                                     command=self._on_delete)
        self.btn_delete.pack(side="left", padx=4)

    # ================================================================ 数据刷新
    def _current_filter(self):
        status_text = self.combo_status.get()
        status = dict((t, f) for t, f in STATUS_FILTERS).get(status_text, FILTER_ALL)
        prio_text = self.combo_priority_filter.get()
        priority = None
        if prio_text in PRIORITY_TEXT:
            priority = PRIORITY_TEXT[prio_text]
        return status, priority

    def refresh(self):
        """按当前筛选条件重绘列表并保留选择。"""
        keep_id = self._selected_id()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._iids = {}

        status, priority = self._current_filter()
        todos = self.manager.list_todos(status=status, priority=priority)
        for todo in todos:
            state_text = "已完成" if todo.done else "进行中"
            if todo.done:
                state_char = "☑"
            else:
                state_char = "☐"
            tags = ["p_%s" % ("high" if todo.priority == PRIORITY_HIGH
                              else "medium" if todo.priority == PRIORITY_MEDIUM
                              else "low")]
            if todo.done:
                tags.append("done")
            if not todo.done and todo.is_overdue:
                tags.append("overdue")
            due_text = todo.due or "—"
            iid = self.tree.insert(
                "", "end",
                values=(state_char, todo.priority_name, todo.title,
                        due_text, todo.pomodoros, todo.created_at),
                tags=tags)
            self._iids[todo.id] = iid

        if keep_id is not None and keep_id in self._iids:
            self.tree.selection_set(self._iids[keep_id])
            self.tree.focus(self._iids[keep_id])

        summary = self.manager.summary()
        self.summary_label.config(
            text="共 %d 条 · 进行中 %d · 已完成 %d · 完成率 %.0f%%"
                 % (summary["total"], summary["active"], summary["done"],
                    summary["rate"]))
        self._on_select()

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        for tid, iid in self._iids.items():
            if iid == sel[0]:
                return tid
        return None

    def _selected_row(self):
        tid = self._selected_id()
        return self.manager.get(tid) if tid is not None else None

    # ================================================================ 事件
    def _on_select(self, _event=None):
        has = self._selected_id() is not None
        state = "!disabled" if has else "disabled"
        self.btn_toggle.state([state])
        self.btn_edit.state([state])
        self.btn_delete.state([state])

    def _on_double_click(self, _event):
        if self._selected_id() is not None:
            self._on_toggle_done()

    def _on_toggle_done(self):
        todo = self._selected_row()
        if todo is None:
            return
        self.manager.toggle_done(todo.id)
        if self._editing_id == todo.id:
            self._cancel_edit()
        self.refresh()

    def _on_delete(self):
        todo = self._selected_row()
        if todo is None:
            return
        if messagebox.askyesno("删除确认",
                               "确定删除待办「%s」吗？" % todo.title):
            self.manager.delete(todo.id)
            if self._editing_id == todo.id:
                self._cancel_edit()
            self.refresh()

    def _on_edit(self):
        todo = self._selected_row()
        if todo is None:
            return
        self._editing_id = todo.id
        self.entry_title.delete(0, "end")
        self.entry_title.insert(0, todo.title)
        self.entry_note.delete(0, "end")
        self.entry_note.insert(0, todo.note)
        self.entry_due.delete(0, "end")
        self.entry_due.insert(0, todo.due)
        self.combo_priority.set(PRIORITY_NAMES.get(todo.priority, "中"))
        self.btn_save.config(text="保存修改")
        self.btn_cancel_edit.state(["!disabled"])
        self.entry_title.focus_set()

    def _cancel_edit(self):
        self._editing_id = None
        self._clear_inputs()
        self.btn_save.config(text="＋ 添加")
        self.btn_cancel_edit.state(["disabled"])

    def _clear_inputs(self):
        self.entry_title.delete(0, "end")
        self.entry_note.delete(0, "end")
        self.entry_due.delete(0, "end")
        self.combo_priority.set("中")

    def _on_save(self):
        title = self.entry_title.get().strip()
        if not title:
            messagebox.showwarning("提示", "请填写待办内容")
            return
        due = self.entry_due.get().strip()
        if due and not _DUE_RE.match(due):
            messagebox.showwarning("格式错误",
                                   "截止日期请使用 YYYY-MM-DD 格式，如 2025-12-31")
            return
        priority = PRIORITY_TEXT.get(self.combo_priority.get(), PRIORITY_MEDIUM)
        note = self.entry_note.get().strip()
        try:
            if self._editing_id is not None:
                self.manager.update(self._editing_id, title=title, note=note,
                                    priority=priority, due=due)
            else:
                self.manager.add(title, note=note, priority=priority, due=due)
        except ValueError as exc:
            messagebox.showerror("保存失败", str(exc))
            return
        self._cancel_edit()
        self.refresh()

    def on_show(self):
        """切换到本页时刷新，确保数据最新。"""
        self.refresh()
