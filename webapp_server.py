"""
Модуль встроенного веб-сервера Telegram Mini App (Web App) для проекта «Анкета».
Предоставляет всплывающее диалоговое окно чата с клиентом прямо внутри Telegram.
"""

import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any

from aiohttp import web
from aiogram import Bot

import database as db

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Диалог с клиентом</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {
            --bg: var(--tg-theme-bg-color, #ffffff);
            --secondary-bg: var(--tg-theme-secondary-bg-color, #f4f4f5);
            --text: var(--tg-theme-text-color, #000000);
            --hint: var(--tg-theme-hint-color, #8e8e93);
            --link: var(--tg-theme-link-color, #2481cc);
            --btn: var(--tg-theme-button-color, #3390ec);
            --btn-text: var(--tg-theme-button-text-color, #ffffff);
            --msg-in: var(--tg-theme-secondary-bg-color, #f0f0f2);
            --msg-out: var(--tg-theme-button-color, #3390ec);
            --msg-out-text: var(--tg-theme-button-text-color, #ffffff);
            --border: rgba(0,0,0,0.08);
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }
        body {
            background-color: var(--bg);
            color: var(--text);
            display: flex;
            flex-direction: column;
            height: 100vh;
            height: 100dvh;
            overflow: hidden;
        }
        /* Шапка */
        .header {
            background-color: var(--bg);
            border-bottom: 1px solid var(--border);
            padding: 10px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }
        .user-info {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #6366f1, #a855f7);
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 16px;
            text-transform: uppercase;
        }
        .user-details h2 {
            font-size: 15px;
            font-weight: 600;
            line-height: 1.2;
        }
        .user-details p {
            font-size: 12px;
            color: var(--hint);
        }
        .header-actions {
            display: flex;
            gap: 8px;
        }
        .btn-action {
            background: var(--secondary-bg);
            border: 1px solid var(--border);
            color: var(--text);
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-action:active {
            transform: scale(0.96);
        }
        .btn-close-chat {
            background: #fee2e2;
            color: #b91c1c;
            border-color: #fecaca;
        }

        /* Выдвижная панель анкеты */
        .anketa-drawer {
            display: none;
            background: var(--secondary-bg);
            border-bottom: 1px solid var(--border);
            padding: 12px 16px;
            font-size: 13px;
            max-height: 35vh;
            overflow-y: auto;
            flex-shrink: 0;
        }
        .anketa-drawer.open {
            display: block;
        }
        .anketa-title {
            font-weight: 600;
            margin-bottom: 6px;
            color: var(--link);
        }
        .anketa-section {
            margin-bottom: 8px;
            line-height: 1.4;
        }
        .anketa-section b {
            color: var(--text);
        }

        /* Область сообщений */
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 14px 16px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            background: var(--secondary-bg);
        }
        .empty-state {
            margin: auto;
            text-align: center;
            color: var(--hint);
            font-size: 13px;
        }
        .empty-state svg {
            width: 44px;
            height: 44px;
            stroke: var(--hint);
            margin-bottom: 8px;
            opacity: 0.6;
        }

        /* Пузыри сообщений */
        .message-row {
            display: flex;
            flex-direction: column;
            max-width: 82%;
        }
        .message-row.client {
            align-self: flex-start;
        }
        .message-row.operator {
            align-self: flex-end;
        }
        .bubble {
            padding: 9px 13px;
            border-radius: 14px;
            font-size: 14px;
            line-height: 1.4;
            word-wrap: break-word;
            position: relative;
            box-shadow: 0 1px 2px rgba(0,0,0,0.06);
        }
        .message-row.client .bubble {
            background-color: var(--bg);
            color: var(--text);
            border-bottom-left-radius: 3px;
        }
        .message-row.operator .bubble {
            background-color: var(--msg-out);
            color: var(--msg-out-text);
            border-bottom-right-radius: 3px;
        }
        .msg-time {
            font-size: 10px;
            margin-top: 3px;
            opacity: 0.7;
            align-self: flex-end;
        }
        .message-row.client .msg-time {
            color: var(--hint);
        }
        .message-row.operator .msg-time {
            color: rgba(255,255,255,0.85);
        }

        /* Нижняя панель ввода */
        .input-bar {
            background-color: var(--bg);
            border-top: 1px solid var(--border);
            padding: 10px 14px;
            display: flex;
            align-items: center;
            gap: 10px;
            flex-shrink: 0;
        }
        .input-bar textarea {
            flex: 1;
            background: var(--secondary-bg);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 9px 15px;
            font-size: 14px;
            line-height: 1.3;
            resize: none;
            max-height: 100px;
            min-height: 38px;
            outline: none;
            transition: border-color 0.2s;
        }
        .input-bar textarea:focus {
            border-color: var(--link);
        }
        .btn-send {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: var(--btn);
            color: var(--btn-text);
            border: none;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            flex-shrink: 0;
            transition: transform 0.15s, opacity 0.2s;
        }
        .btn-send:active {
            transform: scale(0.92);
        }
        .btn-send:disabled {
            opacity: 0.4;
            cursor: default;
        }
        .btn-send svg {
            width: 18px;
            height: 18px;
            fill: currentColor;
            transform: translateX(1px);
        }
        .toast {
            position: fixed;
            top: 60px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            color: #fff;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 100;
        }
        .toast.show {
            opacity: 1;
        }
    </style>
</head>
<body>
    <div id="toast" class="toast"></div>

    <!-- Шапка чата -->
    <div class="header">
        <div class="user-info">
            <div id="userAvatar" class="avatar">?</div>
            <div class="user-details">
                <h2 id="userName">Загрузка...</h2>
                <p id="userStatus">🟢 В сети</p>
            </div>
        </div>
        <div class="header-actions">
            <button class="btn-action" onclick="toggleAnketa()">📋 Анкета</button>
            <button class="btn-action btn-close-chat" onclick="closeDialog()">❌ Завершить</button>
        </div>
    </div>

    <!-- Выдвижная карточка анкеты -->
    <div id="anketaDrawer" class="anketa-drawer">
        <div class="anketa-title">📋 Сводка клиента</div>
        <div class="anketa-section">
            <b>🧴 Уход (Вопрос 7):</b> <span id="careAnswer">—</span>
        </div>
        <div class="anketa-section">
            <b>📊 Результаты разбора кожи:</b>
            <div id="analysisText" style="white-space: pre-wrap; margin-top: 4px; font-size: 12px; color: var(--hint);">—</div>
        </div>
    </div>

    <!-- Область сообщений -->
    <div id="chatMessages" class="chat-container">
        <div class="empty-state">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p>Загрузка сообщений...</p>
        </div>
    </div>

    <!-- Поле ввода -->
    <div class="input-bar">
        <textarea id="messageInput" placeholder="Напишите сообщение клиенту..." rows="1" oninput="autoGrow(this)" onkeydown="checkEnter(event)"></textarea>
        <button id="sendBtn" class="btn-send" onclick="sendMessage()">
            <svg viewBox="0 0 24 24">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
        </button>
    </div>

    <script>
        const tg = window.Telegram?.WebApp;
        if (tg) {
            tg.ready();
            tg.expand();
        }

        const urlParams = new URLSearchParams(window.location.search);
        const clientId = parseInt(urlParams.get('client_id') || "0");
        const operatorId = parseInt(urlParams.get('operator_id') || tg?.initDataUnsafe?.user?.id || "7875791813");

        let lastMessageCount = 0;
        let isSending = false;

        function showToast(text) {
            const toast = document.getElementById('toast');
            toast.innerText = text;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2500);
        }

        function toggleAnketa() {
            const drawer = document.getElementById('anketaDrawer');
            drawer.classList.toggle('open');
        }

        function autoGrow(el) {
            el.style.height = "38px";
            el.style.height = Math.min(el.scrollHeight, 100) + "px";
        }

        function checkEnter(e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.innerText = text || '';
            return div.innerHTML;
        }

        async function fetchHistory() {
            if (!clientId) return;
            try {
                const res = await fetch(`/api/history?client_id=${clientId}`);
                if (!res.ok) return;
                const data = await res.json();

                // Обновляем информацию пользователя
                const name = data.client_name || `Клиент ${clientId}`;
                document.getElementById('userName').innerText = name;
                document.getElementById('userAvatar').innerText = name.charAt(0) || 'К';
                const userText = data.username ? `@${data.username}` : `ID: ${clientId}`;
                document.getElementById('userStatus').innerText = `🟢 ${userText}`;

                if (data.care_answer) {
                    document.getElementById('careAnswer').innerText = data.care_answer;
                }
                if (data.analysis_text) {
                    document.getElementById('analysisText').innerText = data.analysis_text;
                }

                // Рендерим сообщения
                const messages = data.messages || [];
                const container = document.getElementById('chatMessages');

                if (messages.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <p>Диалог пуст. Напишите первое сообщение клиенту!</p>
                        </div>
                    `;
                    lastMessageCount = 0;
                    return;
                }

                if (messages.length !== lastMessageCount) {
                    let html = '';
                    messages.forEach(m => {
                        const isClient = (m.sender_type === 'client');
                        const rowClass = isClient ? 'client' : 'operator';
                        const time = (m.created_at || '').split(' ')[1] || '';
                        html += `
                            <div class="message-row ${rowClass}">
                                <div class="bubble">
                                    ${escapeHtml(m.text)}
                                    <div class="msg-time">${time}</div>
                                </div>
                            </div>
                        `;
                    });
                    container.innerHTML = html;
                    lastMessageCount = messages.length;
                    container.scrollTop = container.scrollHeight;
                }
            } catch (err) {
                console.error("Ошибка загрузки истории:", err);
            }
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const text = input.value.trim();
            if (!text || isSending || !clientId) return;

            isSending = true;
            const btn = document.getElementById('sendBtn');
            btn.disabled = true;

            try {
                const res = await fetch('/api/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        client_id: clientId,
                        operator_id: operatorId,
                        text: text
                    })
                });
                const resData = await res.json();
                if (resData.ok) {
                    input.value = '';
                    input.style.height = "38px";
                    await fetchHistory();
                } else {
                    showToast(resData.error || 'Ошибка отправки');
                }
            } catch (e) {
                showToast('Ошибка сети');
            } finally {
                isSending = false;
                btn.disabled = false;
                input.focus();
            }
        }

        async function closeDialog() {
            if (!confirm('Завершить диалог с этим клиентом?')) return;
            try {
                const res = await fetch('/api/close', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        client_id: clientId,
                        operator_id: operatorId
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast('Диалог завершён');
                    if (tg) {
                        tg.close();
                    } else {
                        window.location.reload();
                    }
                }
            } catch (e) {
                showToast('Не удалось завершить диалог');
            }
        }

        // Первичная загрузка и периодический опрос (polling) каждые 2 секунды
        fetchHistory();
        setInterval(fetchHistory, 2000);
    </script>
</body>
</html>
"""


class WebAppServer:
    def __init__(self, bot: Bot, port: int = 8080):
        self.bot = bot
        self.port = port
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/chat', self.handle_chat_page)
        self.app.router.add_get('/chat/{client_id}', self.handle_chat_page_path)
        self.app.router.add_get('/api/history', self.handle_get_history)
        self.app.router.add_post('/api/send', self.handle_send_message)
        self.app.router.add_post('/api/close', self.handle_close_dialog)

    async def handle_index(self, request: web.Request) -> web.Response:
        return web.Response(text="Telegram WebApp CRM Server is running.", content_type="text/plain")

    async def handle_chat_page(self, request: web.Request) -> web.Response:
        return web.Response(text=HTML_TEMPLATE, content_type="text/html")

    async def handle_chat_page_path(self, request: web.Request) -> web.Response:
        return web.Response(text=HTML_TEMPLATE, content_type="text/html")

    async def handle_get_history(self, request: web.Request) -> web.Response:
        client_id_str = request.query.get("client_id")
        if not client_id_str or not client_id_str.isdigit():
            return web.json_response({"error": "client_id is required"}, status=400)
        
        client_id = int(client_id_str)
        user_info = db.get_user(client_id) or {}
        messages = db.get_chat_history(client_id, limit=50)

        data = {
            "client_id": client_id,
            "client_name": user_info.get("user_name") or f"Клиент {client_id}",
            "username": user_info.get("username"),
            "care_answer": user_info.get("care_answer"),
            "analysis_text": user_info.get("analysis_text"),
            "messages": messages
        }
        return web.json_response(data)

    async def handle_send_message(self, request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

        client_id = body.get("client_id")
        operator_id = body.get("operator_id") or 7875791813
        text = (body.get("text") or "").strip()

        if not client_id or not text:
            return web.json_response({"ok": False, "error": "client_id and text required"}, status=400)

        try:
            # 1. Отправляем сообщение клиенту в Telegram
            sent = await self.bot.send_message(chat_id=client_id, text=text)

            # 2. Сохраняем в БД истории
            db.save_chat_message(
                client_id=client_id,
                sender_type="operator",
                sender_id=operator_id,
                text=text,
                media_type="text"
            )

            # 3. Дублируем оператору в ЛС (если сообщение отправлено через Web App)
            try:
                await self.bot.send_message(
                    chat_id=operator_id,
                    text=f"📤 <i>(Web App ➡️ {client_id}):</i>\n{text}",
                    parse_mode="HTML"
                )
            except Exception:
                pass

            return web.json_response({"ok": True, "message_id": sent.message_id})
        except Exception as e:
            logger.error(f"Ошибка отправки через WebApp клиенту {client_id}: {e}")
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def handle_close_dialog(self, request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

        client_id = body.get("client_id")
        operator_id = body.get("operator_id") or 7875791813

        if not client_id:
            return web.json_response({"ok": False, "error": "client_id required"}, status=400)

        db.close_active_dialog_for_operator(operator_id, client_id)
        try:
            await self.bot.send_message(chat_id=client_id, text="Диалог закончен.")
        except Exception:
            pass

        try:
            await self.bot.send_message(
                chat_id=operator_id,
                text=f"Диалог с клиентом {client_id} завершён через диалоговое окно."
            )
        except Exception:
            pass

        return web.json_response({"ok": True})

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"🌐 Сервер Telegram Web App запущен на http://0.0.0.0:{self.port}")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            logger.info("🌐 Сервер Telegram Web App остановлен.")
