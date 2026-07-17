// Hy3 RAG frontend logic
(() => {
    "use strict";

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => Array.from(document.querySelectorAll(sel));

    const refs = {
        docPanel: $("#docPanel"),
        uploadDrop: $("#uploadDrop"),
        fileInput: $("#fileInput"),
        folderTabs: $("#folderTabs"),
        docList: $("#docList"),
        chatMessages: $("#chatMessages"),
        emptyState: $("#emptyState"),
        questionInput: $("#questionInput"),
        sendBtn: $("#sendBtn"),
        chatInputWrapper: $("#chatInputWrapper"),
        docContextInline: $("#docContextInline"),
        connStatus: $("#connStatus"),
        chatTitle: $("#chatTitle"),
        sidebarConvList: $("#sidebarConvList"),
        sidebarNewConvBtn: $("#sidebarNewConvBtn"),
        menuBtn: $("#menuBtn"),
        menuModal: $("#menuModal"),
        menuClose: $("#menuClose"),
        menuDocMgmt: $("#menuDocMgmt"),
        menuConvMgmt: $("#menuConvMgmt"),
        convModal: $("#convModal"),
        convClose: $("#convClose"),
        convModalList: $("#convModalList"),
        docModal: $("#docModal"),
        docClose: $("#docClose"),
        docModalList: $("#docModalList"),
    };

    // ── State ─────────────────────────────────────────────
    let docs = [];
    let folders = [];
    let conversations = [];
    let activeFolderId = null;
    let selectedDocs = [];       // doc names pinned to the input as context
    let currentConvId = null;
    let isGenerating = false;

    // ── Helpers ───────────────────────────────────────────
    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, (c) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
        }[c]));
    }
    function escapeJs(s) { return escapeHtml(s); }

    function getDocIconClass(fn) {
        const ext = fn.slice(fn.lastIndexOf(".") + 1).toLowerCase();
        if (["pdf"].includes(ext)) return "pdf";
        if (["docx", "doc"].includes(ext)) return "docx";
        if (["txt"].includes(ext)) return "txt";
        if (["md"].includes(ext)) return "md";
        return "other";
    }
    function getDocIconLetter(fn) {
        const ext = fn.slice(fn.lastIndexOf(".") + 1).toLowerCase();
        return (ext || "?").slice(0, 3).toUpperCase();
    }

    function renderMarkdown(text) {
        let html = escapeHtml(text);
        html = html.replace(/```([\s\S]*?)```/g, (_, c) => `<pre><code>${c}</code></pre>`);
        html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
        html = html.replace(/\n/g, "<br>");
        return html;
    }

    // ── Health ────────────────────────────────────────────
    async function checkHealth() {
        try {
            const r = await fetch("/api/health");
            const d = await r.json();
            if (d.status === "ok") {
                refs.connStatus.textContent = "已连接 · " + d.documents + " 篇文档";
                refs.connStatus.className = "chat-status ok";
            } else {
                refs.connStatus.textContent = "未配置 API Key";
                refs.connStatus.className = "chat-status err";
            }
        } catch (e) {
            refs.connStatus.textContent = "连接失败";
            refs.connStatus.className = "chat-status err";
        }
    }

    // ── Documents ─────────────────────────────────────────
    async function loadDocuments() {
        try {
            const url = activeFolderId
                ? `/api/documents?folder_id=${encodeURIComponent(activeFolderId)}`
                : "/api/documents";
            const r = await fetch(url);
            const d = await r.json();
            docs = d.documents || [];
            renderDocList();
        } catch (e) {
            console.error(e);
        }
    }

    function renderDocList() {
        if (!docs.length) {
            refs.docList.innerHTML = `<div class="doc-meta" style="padding:8px">暂无文档，请先上传。</div>`;
            return;
        }
        refs.docList.innerHTML = docs.map((d) => `
            <div class="doc-item" draggable="true" data-filename="${escapeHtml(d.filename)}">
                <div class="doc-icon ${getDocIconClass(d.filename)}">${getDocIconLetter(d.filename)}</div>
                <div class="doc-info">
                    <div class="doc-name" title="${escapeHtml(d.filename)}">${escapeHtml(d.filename)}</div>
                    <div class="doc-meta">${d.chunk_count} 个片段 · ${d.file_type || ""}</div>
                </div>
                <button class="doc-delete" onclick="deleteDocument('${escapeJs(d.filename)}')" title="删除">&times;</button>
            </div>
        `).join("");
    }

    window.deleteDocument = async function (filename) {
        if (!confirm(`确定删除文档「${filename}」？`)) return;
        await fetch(`/api/documents/${encodeURIComponent(filename)}`, { method: "DELETE" });
        selectedDocs = selectedDocs.filter((f) => f !== filename);
        renderContextInline();
        loadDocuments();
    };

    // Upload
    refs.fileInput.addEventListener("change", (e) => handleFiles(e.target.files));
    refs.uploadDrop.addEventListener("dragover", (e) => {
        e.preventDefault();
        refs.uploadDrop.classList.add("drag-over");
    });
    refs.uploadDrop.addEventListener("dragleave", () => refs.uploadDrop.classList.remove("drag-over"));
    refs.uploadDrop.addEventListener("drop", (e) => {
        e.preventDefault();
        refs.uploadDrop.classList.remove("drag-over");
        handleFiles(e.dataTransfer.files);
    });

    async function handleFiles(fileList) {
        for (const file of fileList) {
            const fd = new FormData();
            fd.append("file", file);
            try {
                const r = await fetch("/api/documents/upload", { method: "POST", body: fd });
                if (!r.ok) {
                    const err = await r.json().catch(() => ({}));
                    alert("上传失败: " + (err.detail || r.status));
                    continue;
                }
            } catch (e) {
                alert("上传失败: " + e.message);
                continue;
            }
        }
        loadDocuments();
        checkHealth();
    }

    // ── Folders ───────────────────────────────────────────
    async function loadFolders() {
        try {
            const r = await fetch("/api/folders");
            const d = await r.json();
            folders = d.folders || [];
            renderFolderTabs();
        } catch (e) { console.error(e); }
    }

    function renderFolderTabs() {
        let html = `<button class="folder-tab ${activeFolderId === null ? "active" : ""}" data-folder-id="">全部</button>`;
        for (const f of folders) {
            const isActive = activeFolderId === f.id;
            html += `<button class="folder-tab ${isActive ? "active" : ""}" data-folder-id="${f.id}">📁 ${escapeHtml(f.name)}</button>`;
        }
        refs.folderTabs.innerHTML = html;
    }

    refs.folderTabs.addEventListener("click", (e) => {
        const tab = e.target.closest(".folder-tab");
        if (!tab) return;
        const id = tab.dataset.folderId;
        activeFolderId = id === "" ? null : id;
        renderFolderTabs();
        loadDocuments();
    });

    // ── Context chips (drag doc into input) ───────────────
    refs.chatInputWrapper.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "copy";
        refs.chatInputWrapper.classList.add("drag-over");
    });
    refs.chatInputWrapper.addEventListener("dragleave", () => refs.chatInputWrapper.classList.remove("drag-over"));
    refs.chatInputWrapper.addEventListener("drop", (e) => {
        e.preventDefault();
        refs.chatInputWrapper.classList.remove("drag-over");
        const filename = e.dataTransfer.getData("text/plain");
        if (filename && !selectedDocs.includes(filename)) {
            selectedDocs.push(filename);
            renderContextInline();
        }
    });

    // Make sidebar docs draggable
    refs.docList.addEventListener("dragstart", (e) => {
        const item = e.target.closest(".doc-item");
        if (!item) return;
        e.dataTransfer.setData("text/plain", item.dataset.filename);
        e.dataTransfer.effectAllowed = "copy";
    });

    function renderContextInline() {
        if (!selectedDocs.length) {
            refs.docContextInline.classList.add("hidden");
            refs.docContextInline.innerHTML = "";
            return;
        }
        refs.docContextInline.classList.remove("hidden");
        refs.docContextInline.innerHTML = selectedDocs.map((fn) => {
            const ic = getDocIconClass(fn);
            const il = getDocIconLetter(fn);
            return `<span class="context-chip" data-filename="${escapeHtml(fn)}">
                <span class="context-chip-docicon ${ic}">${il}</span>
                ${escapeHtml(fn)}
                <button class="context-chip-remove" data-remove="${escapeHtml(fn)}" title="移除">&times;</button>
            </span>`;
        }).join("");

        $$(".context-chip-remove", ).forEach((btn) => {});
        Array.from(refs.docContextInline.querySelectorAll(".context-chip-remove")).forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const fn = btn.dataset.remove;
                selectedDocs = selectedDocs.filter((d) => d !== fn);
                renderContextInline();
            });
        });
    }

    // ── Conversations ──────────────────────────────────────
    async function loadConversations() {
        try {
            const r = await fetch("/api/conversations");
            const d = await r.json();
            conversations = d.conversations || [];
            renderConvList();
        } catch (e) { console.error(e); }
    }

    function renderConvList() {
        if (!conversations.length) {
            refs.sidebarConvList.innerHTML = `<div class="doc-meta" style="padding:8px">暂无历史对话</div>`;
            return;
        }
        refs.sidebarConvList.innerHTML = conversations.map((c) => `
            <div class="conv-row ${c.id === currentConvId ? "active" : ""}" data-conv-id="${c.id}">
                <span class="conv-title" title="${escapeHtml(c.title)}">${escapeHtml(c.title)}</span>
                <button class="conv-del" data-del="${c.id}" title="删除">&times;</button>
            </div>
        `).join("");
    }

    refs.sidebarConvList.addEventListener("click", (e) => {
        const del = e.target.closest(".conv-del");
        if (del) {
            e.stopPropagation();
            const id = del.dataset.del;
            fetch(`/api/conversations/${id}`, { method: "DELETE" }).then(() => {
                if (currentConvId === id) newConversation();
                loadConversations();
            });
            return;
        }
        const row = e.target.closest(".conv-row");
        if (row) selectConversation(row.dataset.convId);
    });

    refs.sidebarNewConvBtn.addEventListener("click", () => newConversation());

    function newConversation() {
        currentConvId = null;
        selectedDocs = [];
        renderContextInline();
        refs.chatMessages.innerHTML = "";
        refs.emptyState.style.display = "block";
        refs.chatTitle.textContent = "Hy3 RAG 问答";
        renderConvList();
    }

    async function selectConversation(convId) {
        try {
            const r = await fetch(`/api/conversations/${convId}`);
            const d = await r.json();
            const conv = d.conversation;
            currentConvId = convId;
            selectedDocs = [];
            renderContextInline();
            refs.emptyState.style.display = "none";
            refs.chatMessages.innerHTML = "";
            (conv.messages || []).forEach((m) => appendMessage(m.role, m.content, false));
            refs.chatTitle.textContent = conv.title || "对话";
            renderConvList();
        } catch (e) { console.error(e); }
    }

    // ── Messaging ─────────────────────────────────────────
    function appendMessage(role, content, render) {
        const empty = refs.emptyState;
        if (empty) empty.style.display = "none";
        const div = document.createElement("div");
        div.className = `msg ${role}`;
        const avatar = role === "user" ? "我" : "H";
        div.innerHTML = `
            <div class="msg-avatar">${avatar}</div>
            <div class="msg-bubble">${render ? renderMarkdown(content) : escapeHtml(content)}</div>
        `;
        refs.chatMessages.appendChild(div);
        refs.chatMessages.scrollTop = refs.chatMessages.scrollHeight;
        return div;
    }

    function appendTyping() {
        const div = document.createElement("div");
        div.className = "msg assistant";
        div.innerHTML = `<div class="msg-avatar">H</div><div class="msg-bubble"><span class="typing"><span></span><span></span><span></span></span></div>`;
        refs.chatMessages.appendChild(div);
        refs.chatMessages.scrollTop = refs.chatMessages.scrollHeight;
        return div;
    }

    async function sendQuestion() {
        const question = refs.questionInput.value.trim();
        if (!question || isGenerating) return;

        appendMessage("user", question, false);
        refs.questionInput.value = "";
        autoResize();
        isGenerating = true;
        refs.sendBtn.classList.add("loading");
        refs.sendBtn.disabled = true;

        const body = { question, top_k: 6 };
        if (currentConvId) body.conversation_id = currentConvId;
        if (activeFolderId) body.folder_id = activeFolderId;
        if (selectedDocs.length) body.source_filters = selectedDocs;

        const typing = appendTyping();
        let answerEl = null;
        let fullAnswer = "";
        let sources = [];

        try {
            const r = await fetch("/api/qa/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            const reader = r.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop();
                for (const line of lines) {
                    if (!line.startsWith("data:")) continue;
                    const payload = line.slice(5).trim();
                    if (!payload) continue;
                    let ev;
                    try { ev = JSON.parse(payload); } catch { continue; }

                    if (ev.type === "context") {
                        sources = ev.sources || [];
                    } else if (ev.type === "token") {
                        fullAnswer += ev.content;
                        if (!answerEl) {
                            typing.remove();
                            answerEl = appendMessage("assistant", fullAnswer, true);
                        } else {
                            answerEl.querySelector(".msg-bubble").innerHTML = renderMarkdown(fullAnswer);
                        }
                        refs.chatMessages.scrollTop = refs.chatMessages.scrollHeight;
                    } else if (ev.type === "conversation") {
                        if (!currentConvId) currentConvId = ev.conversation_id;
                    } else if (ev.type === "done") {
                        fullAnswer = ev.answer || fullAnswer;
                        sources = ev.sources ? [...new Set(ev.sources.map((s) => s.doc_name).filter(Boolean))] : sources;
                    } else if (ev.type === "error") {
                        typing.remove();
                        appendMessage("assistant", "⚠️ " + ev.message, false);
                    }
                }
            }
            // Render sources
            if (answerEl && sources.length) {
                const srcHtml = `<div class="sources">${sources.map((s) => `<span class="source-tag">📄 ${escapeHtml(s)}</span>`).join("")}</div>`;
                answerEl.querySelector(".msg-bubble").innerHTML += srcHtml;
            }
            loadConversations();
        } catch (e) {
            typing.remove();
            appendMessage("assistant", "⚠️ 请求失败: " + e.message, false);
        } finally {
            isGenerating = false;
            refs.sendBtn.classList.remove("loading");
            refs.sendBtn.disabled = false;
        }
    }

    function autoResize() {
        refs.questionInput.style.height = "auto";
        refs.questionInput.style.height = Math.min(refs.questionInput.scrollHeight, 140) + "px";
    }

    refs.questionInput.addEventListener("input", autoResize);
    refs.questionInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendQuestion();
        }
    });
    refs.sendBtn.addEventListener("click", sendQuestion);

    // ── Modals ────────────────────────────────────────────
    function openModal(m) { m.classList.add("show"); }
    function closeModal(m) { m.classList.remove("show"); }

    refs.menuBtn.addEventListener("click", () => openModal(refs.menuModal));
    refs.menuClose.addEventListener("click", () => closeModal(refs.menuModal));
    refs.convClose.addEventListener("click", () => closeModal(refs.convModal));
    refs.docClose.addEventListener("click", () => closeModal(refs.docModal));
    [refs.menuModal, refs.convModal, refs.docModal].forEach((m) =>
        m.addEventListener("click", (e) => { if (e.target === m) closeModal(m); }));

    refs.menuDocMgmt.addEventListener("click", () => { closeModal(refs.menuModal); openDocModal(); });
    refs.menuConvMgmt.addEventListener("click", () => { closeModal(refs.menuModal); openConvModal(); });

    async function openDocModal() {
        await loadDocuments();
        const list = docs.length
            ? docs.map((d) => `<div class="mgmt-row"><span class="mgmt-title">${escapeHtml(d.filename)}</span>
                <button class="mgmt-del" onclick="deleteDocument('${escapeJs(d.filename)}')">&times;</button></div>`).join("")
            : `<div class="doc-meta">暂无文档</div>`;
        refs.docModalList.innerHTML = list;
        openModal(refs.docModal);
    }

    async function openConvModal() {
        await loadConversations();
        const list = conversations.length
            ? conversations.map((c) => `<div class="mgmt-row"><span class="mgmt-title">${escapeHtml(c.title)}</span>
                <button class="mgmt-del" data-del="${c.id}">&times;</button></div>`).join("")
            : `<div class="doc-meta">暂无对话</div>`;
        refs.convModalList.innerHTML = list;
        Array.from(refs.convModalList.querySelectorAll(".mgmt-del")).forEach((b) => {
            b.addEventListener("click", () => {
                fetch(`/api/conversations/${b.dataset.del}`, { method: "DELETE" }).then(() => {
                    if (currentConvId === b.dataset.del) newConversation();
                    openConvModal();
                });
            });
        });
        openModal(refs.convModal);
    }

    // ── Init ──────────────────────────────────────────────
    async function init() {
        await checkHealth();
        await loadFolders();
        await loadDocuments();
        await loadConversations();
    }
    init();
})();
