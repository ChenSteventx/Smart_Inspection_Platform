const express = require('express');
const puppeteer = require('puppeteer-core');
const WebSocket = require('ws');
const http = require('http');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ 
    server,
    perMessageDeflate: false
});

const port = process.argv[2] || 8081;
const defaultURL = process.argv[3] || 'https://fh.dji.com';

class HeadlessStreamingBrowser {
    constructor() {
        this.browser = null;
        this.page = null;
        this.clients = new Map();
        this.cdpSession = null;
        this.isInitialized = false;
        this.targetFPS = 20;
        this.performanceMode = 'balanced';
        this.lastFrameTime = 0;
        this.minFrameInterval = 1000 / this.targetFPS;
        
        // 事件节流相关
        this.lastEventTime = new Map();
        this.eventThrottle = {
            mousemove: 16, // 60fps limit
            wheel: 33,     // 30fps limit
            drag: 16       // 60fps limit
        };
        
        // 帧优化相关
        this.lastFrameData = null;
        this.frameSkipThreshold = 0.95; // 95%相似度时跳过
        
        // 鼠标状态跟踪
        this.mouseState = {
            leftPressed: false,
            rightPressed: false,
            middlePressed: false
        };
        
        // 页面状态跟踪
        this.pageNavigating = false;
    }

    async initialize() {
        console.log('正在初始化无头浏览器服务...');
        
        try {
            const chromePaths = [
                'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
                process.env.CHROME_PATH
            ].filter(Boolean);
            
            let executablePath = null;
            for (const chromePath of chromePaths) {
                if (fs.existsSync(chromePath)) {
                    executablePath = chromePath;
                    console.log(`找到Chrome: ${chromePath}`);
                    break;
                }
            }

            if (!executablePath) {
                throw new Error('未找到Chrome安装。请确保Chrome已安装或设置CHROME_PATH环境变量。');
            }

            const launchOptions = {
                executablePath: executablePath,
                headless: 'new',
                protocolTimeout: 180000,
                defaultViewport: {
                    width: 1280,
                    height: 800,
                    deviceScaleFactor: 1
                },
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-blink-features=AutomationControlled',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-popup-blocking',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-extensions',
                    '--disable-sync',
                    '--disable-translate',
                    '--metrics-recording-only',
                    '--safebrowsing-disable-auto-update',
                    '--password-store=basic',
                    '--use-mock-keychain',
                    '--force-color-profile=srgb',
                    '--window-size=1280,800',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-ipc-flooding-protection',
                    '--enable-accelerated-2d-canvas',
                    '--enable-gpu-rasterization'
                ],
                ignoreHTTPSErrors: true,
                handleSIGINT: false,
                handleSIGTERM: false,
                handleSIGHUP: false
            };

            console.log('正在启动Chrome...');
            this.browser = await puppeteer.launch(launchOptions);
            console.log('Chrome启动成功');

            this.page = await this.browser.newPage();
            console.log('页面创建成功');
            
            this.page.setDefaultTimeout(60000);
            this.page.setDefaultNavigationTimeout(60000);
            
            await this.page.setUserAgent(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            );
            
            await this.page.evaluateOnNewDocument(() => {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        const plugins = [];
                        for (let i = 0; i < 3; i++) {
                            const plugin = {
                                name: 'Chrome PDF Plugin',
                                filename: 'internal-pdf-viewer',
                                description: 'Portable Document Format',
                                length: 1
                            };
                            plugin[0] = {
                                type: 'application/pdf',
                                suffixes: 'pdf',
                                description: 'Portable Document Format'
                            };
                            plugins.push(plugin);
                        }
                        return plugins;
                    }
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en-US', 'en']
                });
                
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {}
                };
                
                const originalQuery = window.navigator.permissions.query;
                if (originalQuery) {
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                }
            });

            await this.page.setViewport({
                width: 1280,
                height: 800,
                deviceScaleFactor: 1
            });

            this.cdpSession = await this.page.target().createCDPSession();
            await this.setupScreencast();
            
            console.log(`正在导航到: ${defaultURL}`);
            await this.page.goto(defaultURL, {
                waitUntil: 'networkidle2',
                timeout: 60000
            });
            console.log('页面加载完成');

            // 发送初始滚动信息
            setTimeout(async () => {
                await this.sendScrollInfo();
                console.log('初始滚动信息已发送');
            }, 2000);
            this.isInitialized = true;
            console.log('无头浏览器服务初始化完成');
            return true;
            
        } catch (error) {
            console.error('初始化失败:', error.message);
            if (error.stack) {
                console.error('错误堆栈:', error.stack);
            }
            throw error;
        }
    }

    async setupScreencast() {
        try {
            await this.cdpSession.send('Page.enable');
            await this.cdpSession.send('Runtime.enable');
            
            const quality = this.getQualitySettings();
            await this.cdpSession.send('Page.startScreencast', {
                format: 'jpeg',
                quality: quality.jpegQuality,
                maxWidth: quality.maxWidth,
                maxHeight: quality.maxHeight,
                everyNthFrame: 1
            });

            this.cdpSession.on('Page.screencastFrame', async (frameData) => {
                try {
                    await this.cdpSession.send('Page.screencastFrameAck', {
                        sessionId: frameData.sessionId
                    }).catch(err => console.error('Frame ack error:', err));

                    const now = Date.now();
                    if (now - this.lastFrameTime >= this.minFrameInterval && this.clients.size > 0) {
                        
                        // 简单的帧差检测
                        if (this.shouldSkipFrame(frameData.data)) {
                            return;
                        }
                        
                        this.lastFrameTime = now;
                        this.lastFrameData = frameData.data;
                        
                        // 转换为二进制数据
                        const imageBuffer = Buffer.from(frameData.data, 'base64');
                        const message = {
                            type: 'frame',
                            timestamp: now,
                            metadata: frameData.metadata
                        };
                        
                        this.broadcastFrameToClients(message, imageBuffer);
                    }
                } catch (error) {
                    console.error('处理帧数据时出错:', error.message);
                }
            });
        } catch (error) {
            console.error('设置screencast失败:', error);
            throw error;
        }
    }

    shouldSkipFrame(currentFrameData) {
        if (!this.lastFrameData) {
            return false;
        }
        
        // 简单比较：如果数据完全相同则跳过
        return currentFrameData === this.lastFrameData;
    }

    getQualitySettings() {
        const settings = {
            quality: { jpegQuality: 85, maxWidth: 1280, maxHeight: 800 },
            balanced: { jpegQuality: 60, maxWidth: 1024, maxHeight: 640 },
            performance: { jpegQuality: 40, maxWidth: 800, maxHeight: 500 }
        };
        return settings[this.performanceMode];
    }

    broadcastFrameToClients(message, imageBuffer) {
        const messageString = JSON.stringify(message);
        
        this.clients.forEach((client, id) => {
            if (client.readyState === WebSocket.OPEN) {
                try {
                    // 先发送元数据
                    client.send(messageString, (error) => {
                        if (error) {
                            console.error(`向客户端 ${id} 发送元数据失败:`, error);
                            this.removeClient(id);
                            return;
                        }
                        
                        // 再发送图像数据
                        client.send(imageBuffer, (error) => {
                            if (error) {
                                console.error(`向客户端 ${id} 发送图像失败:`, error);
                                this.removeClient(id);
                            }
                        });
                    });
                } catch (error) {
                    console.error(`客户端 ${id} 发送失败:`, error);
                    this.removeClient(id);
                }
            }
        });
    }

    broadcastToClients(message) {
        const messageString = JSON.stringify(message);
        this.clients.forEach((client, id) => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(messageString, (error) => {
                    if (error) {
                        console.error(`向客户端 ${id} 发送失败:`, error);
                        this.removeClient(id);
                    }
                });
            }
        });
    }

    shouldThrottleEvent(eventType, clientId) {
        const throttleTime = this.eventThrottle[eventType];
        if (!throttleTime) return false;
        
        const key = `${clientId}_${eventType}`;
        const now = Date.now();
        const lastTime = this.lastEventTime.get(key) || 0;
        
        if (now - lastTime < throttleTime) {
            return true;
        }
        
        this.lastEventTime.set(key, now);
        return false;
    }

    async handleInteraction(data, clientId = 'default') {
        if (!this.page || !this.isInitialized) {
            console.warn('页面未初始化');
            return;
        }

        // 事件节流检查
        if (this.shouldThrottleEvent(data.type, clientId)) {
            return;
        }

        try {
            const timeout = 30000;
            
            switch (data.type) {
                case 'click':
                    await this.withTimeout(
                        this.safeMouseClick(data.x, data.y),
                        timeout,
                        'Click operation'
                    );
                    break;
                    
                case 'drag':
                    await this.withTimeout(
                        this.performDrag(data),
                        timeout * 2,
                        'Drag operation'
                    );
                    break;
                    
                case 'mousemove':
                    await this.withTimeout(
                        this.page.mouse.move(data.x, data.y, { steps: 1 }),
                        timeout,
                        'Mouse move'
                    );
                    break;
                    
                case 'mousedown':
                    await this.withTimeout(
                        this.safeMouseDown(),
                        timeout,
                        'Mouse down'
                    );
                    break;
                    
                case 'mouseup':
                    await this.withTimeout(
                        this.safeMouseUp(),
                        timeout,
                        'Mouse up'
                    );
                    break;
                    
                case 'wheel':
                    await this.withTimeout(
                        this.page.evaluate((delta) => {
                            window.scrollBy(0, delta.y);
                        }, { y: data.deltaY || 0 }),
                        timeout,
                        'Wheel scroll'
                    );
                    break;
                    
                case 'keypress':
                    if (data.key.length === 1) {
                        await this.withTimeout(
                            this.page.keyboard.type(data.key, { delay: 50 }),
                            timeout,
                            'Key type'
                        );
                    } else {
                        await this.withTimeout(
                            this.page.keyboard.press(data.key),
                            timeout,
                            'Key press'
                        );
                    }
                    break;
                    
                case 'keydown':
                    await this.withTimeout(
                        this.page.keyboard.down(data.key),
                        timeout,
                        'Key down'
                    );
                    break;
                    
                case 'keyup':
                    await this.withTimeout(
                        this.page.keyboard.up(data.key),
                        timeout,
                        'Key up'
                    );
                    break;
                    
                case 'type':
                    // 确保页面可输入
                    await this.ensurePageFocused();
                    await this.withTimeout(
                        this.page.keyboard.type(data.text, { delay: 80 }),
                        timeout,
                        'Text type'
                    );
                    break;
                    
                case 'focus':
                    // 处理元素焦点
                    if (data.selector) {
                        await this.withTimeout(
                            this.page.focus(data.selector),
                            timeout,
                            'Focus element'
                        );
                    }
                    break;
                    
                case 'navigate':
                    this.pageNavigating = true;
                    this.mouseState.leftPressed = false; // 导航时重置鼠标状态
                    
                    await this.page.goto(data.url, {
                        waitUntil: 'networkidle2',
                        timeout: 60000
                    });

                    this.pageNavigating = false;
                    
                    // 导航完成后发送滚动信息
                    setTimeout(async () => {
                        await this.sendScrollInfo();
                    }, 1000);
                    break;
                    
                
                case 'scrollTo':
                    await this.withTimeout(
                        this.page.evaluate((position) => {
                            if (position.scrollLeft !== null) {
                                window.scrollTo(position.scrollLeft, window.pageYOffset);
                            }
                            if (position.scrollTop !== null) {
                                window.scrollTo(window.pageXOffset, position.scrollTop);
                            }
                        }, {
                            scrollLeft: data.scrollLeft,
                            scrollTop: data.scrollTop
                        }),
                        timeout,
                        'Scroll to position'
                    );
                    
                    await this.sendScrollInfo(clientId);
                    break;
                
                case 'getScrollInfo':
                    await this.sendScrollInfo(clientId);
                    break;
        
                case 'refresh':
                    this.pageNavigating = true;
                    this.mouseState.leftPressed = false; // 刷新时重置鼠标状态
                    
                    await this.page.reload({ waitUntil: 'networkidle2' });
                    
                    this.pageNavigating = false;
                    
                    // 刷新完成后发送滚动信息
                    setTimeout(async () => {
                        await this.sendScrollInfo();
                    }, 1000);
                    break;
                    
                case 'back':
                    await this.page.goBack({ waitUntil: 'networkidle2' });
                    break;
                    
                case 'forward':
                    await this.page.goForward({ waitUntil: 'networkidle2' });
                    break;
                    
                case 'setPerformanceMode':
                    await this.setPerformanceMode(data.mode);
                    break;
            }
        } catch (error) {
            console.error('处理交互失败:', error);
            this.broadcastToClients({
                type: 'error',
                message: `操作失败: ${error.message}`
            });
        }
    }


    async sendScrollInfo(clientId = null) {
        try {
            // 检查页面是否在导航中或页面无效
            if (this.pageNavigating || !this.page || !this.isInitialized) {
                console.log('页面不可用，跳过发送滚动信息');
                return;
            }
            
            const scrollData = await this.getPageScrollInfo();
            
            const scrollMessage = {
                type: 'scroll',
                ...scrollData,
                timestamp: Date.now()
            };
            
            if (clientId && this.clients.has(clientId)) {
                const client = this.clients.get(clientId);
                if (client.readyState === WebSocket.OPEN) {
                    client.send(JSON.stringify(scrollMessage));
                }
            } else {
                this.broadcastToClients(scrollMessage);
            }
        } catch (error) {
            // 只在非导航状态下记录错误
            if (!this.pageNavigating) {
                console.error('发送滚动信息失败:', error.message || error);
            }
        }
    }

    async getPageScrollInfo() {
        try {
            // 检查页面状态
            if (!this.page || this.pageNavigating) {
                return this.getDefaultScrollInfo();
            }
            
            // 使用超时保护的方式检查页面是否可用
            const isPageReady = await Promise.race([
                this.page.evaluate(() => {
                    return document.readyState === 'complete' || document.readyState === 'interactive';
                }),
                new Promise(resolve => setTimeout(() => resolve(false), 2000)) // 2秒超时
            ]).catch(() => false);
            
            if (!isPageReady) {
                console.log('页面未准备好，返回默认滚动信息');
                return this.getDefaultScrollInfo();
            }
            
            // 使用超时保护获取滚动信息
            const scrollInfo = await Promise.race([
                this.page.evaluate(() => {
                    try {
                        return {
                            scrollTop: window.pageYOffset || document.documentElement.scrollTop,
                            scrollLeft: window.pageXOffset || document.documentElement.scrollLeft,
                            scrollHeight: Math.max(
                                document.body?.scrollHeight || 0,
                                document.body?.offsetHeight || 0,
                                document.documentElement?.clientHeight || 0,
                                document.documentElement?.scrollHeight || 0,
                                document.documentElement?.offsetHeight || 0
                            ),
                            scrollWidth: Math.max(
                                document.body?.scrollWidth || 0,
                                document.body?.offsetWidth || 0,
                                document.documentElement?.clientWidth || 0,
                                document.documentElement?.scrollWidth || 0,
                                document.documentElement?.offsetWidth || 0
                            ),
                            clientHeight: document.documentElement?.clientHeight || 0,
                            clientWidth: document.documentElement?.clientWidth || 0
                        };
                    } catch (e) {
                        console.log('页面内部获取滚动信息失败:', e);
                        return {
                            scrollTop: 0,
                            scrollLeft: 0,
                            scrollHeight: 0,
                            scrollWidth: 0,
                            clientHeight: 0,
                            clientWidth: 0
                        };
                    }
                }),
                new Promise(resolve => {
                    setTimeout(() => {
                        console.log('获取滚动信息超时，返回默认值');
                        resolve(this.getDefaultScrollInfo());
                    }, 3000); // 3秒超时
                })
            ]);
            
            return scrollInfo;
            
        } catch (error) {
            // 对不同类型的错误进行分类处理
            if (error.message && error.message.includes('Execution context was destroyed')) {
                console.log('页面上下文已销毁（导航中），返回默认滚动信息');
            } else if (error.message && error.message.includes('Target closed')) {
                console.log('页面已关闭，返回默认滚动信息');
            } else {
                console.error('获取页面滚动信息失败:', error.message || error);
            }
            return this.getDefaultScrollInfo();
        }
    }
    
    getDefaultScrollInfo() {
        return {
            scrollTop: 0,
            scrollLeft: 0,
            scrollHeight: 0,
            scrollWidth: 0,
            clientHeight: 0,
            clientWidth: 0
        };
    }

    async withTimeout(promise, timeoutMs, operation) {
        return Promise.race([
            promise,
            new Promise((_, reject) => 
                setTimeout(() => reject(new Error(`${operation} timed out after ${timeoutMs}ms`)), timeoutMs)
            )
        ]);
    }

    async performDrag(data) {
        const steps = 10; // 减少步数提高性能
        const startX = data.startX;
        const startY = data.startY;
        const endX = data.endX;
        const endY = data.endY;
        
        try {
            await this.page.mouse.move(startX, startY);
            await this.page.waitForTimeout(50);
            
            await this.safeMouseDown();
            await this.page.waitForTimeout(50);
            
            for (let i = 0; i <= steps; i++) {
                const progress = i / steps;
                const easeProgress = this.easeInOutQuad(progress);
                
                const x = startX + (endX - startX) * easeProgress;
                const y = startY + (endY - startY) * easeProgress;
                
                await this.page.mouse.move(x, y);
                await this.page.waitForTimeout(10); // 减少等待时间
            }
            
            await this.page.waitForTimeout(50);
            await this.safeMouseUp();
        } catch (error) {
            console.error('拖拽操作失败:', error);
            // 在失败时确保鼠标状态重置
            this.mouseState.leftPressed = false;
            throw error;
        }
    }
    
    async safeMouseClick(x, y) {
        try {
            // 移动到目标位置
            await this.page.mouse.move(x, y);
            await this.page.waitForTimeout(10);
            
            // 确保鼠标在点击前是释放状态
            if (this.mouseState.leftPressed) {
                await this.page.mouse.up();
                this.mouseState.leftPressed = false;
                await this.page.waitForTimeout(20);
            }
            
            // 使用分离的mousedown和mouseup而不是click方法
            await this.page.mouse.down();
            this.mouseState.leftPressed = true;
            await this.page.waitForTimeout(50);
            
            await this.page.mouse.up();
            this.mouseState.leftPressed = false;
            
        } catch (error) {
            console.error('点击操作失败:', error);
            // 确保错误时重置鼠标状态
            this.mouseState.leftPressed = false;
            throw error;
        }
    }
    
    async safeMouseDown() {
        try {
            if (!this.mouseState.leftPressed) {
                await this.page.mouse.down();
                this.mouseState.leftPressed = true;
            }
        } catch (error) {
            console.error('鼠标按下操作失败:', error);
            throw error;
        }
    }
    
    async safeMouseUp() {
        try {
            if (this.mouseState.leftPressed) {
                await this.page.mouse.up();
                this.mouseState.leftPressed = false;
            }
        } catch (error) {
            console.error('鼠标释放操作失败:', error);
            this.mouseState.leftPressed = false; // 即使失败也重置状态
            throw error;
        }
    }

    async ensurePageFocused() {
        try {
            // 确保页面有焦点以接收键盘输入
            await this.page.evaluate(() => {
                // 如果没有元素有焦点，尝试给body焦点
                if (!document.activeElement || document.activeElement === document.body) {
                    // 查找可输入元素
                    const inputElements = document.querySelectorAll('input, textarea, [contenteditable="true"]');
                    if (inputElements.length > 0) {
                        inputElements[0].focus();
                        return;
                    }
                    
                    // 如果没有输入元素，给body焦点
                    if (document.body) {
                        document.body.focus();
                        // 确保body可以接收键盘事件
                        if (!document.body.hasAttribute('tabindex')) {
                            document.body.setAttribute('tabindex', '-1');
                        }
                    }
                }
            });
        } catch (error) {
            console.log('设置页面焦点失败:', error.message);
        }
    }

    easeInOutQuad(t) {
        return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    }

    async setPerformanceMode(mode) {
        if (['quality', 'balanced', 'performance'].includes(mode)) {
            this.performanceMode = mode;
            
            const fpsMap = {
                quality: 30,
                balanced: 20,
                performance: 15
            };
            this.targetFPS = fpsMap[mode];
            this.minFrameInterval = 1000 / this.targetFPS;
            
            await this.cdpSession.send('Page.stopScreencast');
            await this.setupScreencast();
            
            console.log(`性能模式切换到: ${mode}, FPS: ${this.targetFPS}`);
        }
    }

    addClient(ws, id) {
        this.clients.set(id, ws);
        console.log(`客户端 ${id} 已连接，当前连接数: ${this.clients.size}`);
        
        // 当有新客户端连接时重置鼠标状态，防止状态不一致
        this.mouseState.leftPressed = false;
        this.mouseState.rightPressed = false;
        this.mouseState.middlePressed = false;
        
        ws.send(JSON.stringify({
            type: 'connected',
            message: '已连接到无头浏览器服务',
            performanceMode: this.performanceMode,
            supportsBinary: true
        }));
    }

    removeClient(id) {
        this.clients.delete(id);
        this.lastEventTime.delete(`${id}_mousemove`);
        this.lastEventTime.delete(`${id}_wheel`);
        this.lastEventTime.delete(`${id}_drag`);
        console.log(`客户端 ${id} 已断开，当前连接数: ${this.clients.size}`);
    }

    async cleanup() {
        console.log('正在清理资源...');
        
        this.isInitialized = false;
        this.pageNavigating = false;
        
        // 重置鼠标状态
        this.mouseState = {
            leftPressed: false,
            rightPressed: false,
            middlePressed: false
        };
        
        if (this.cdpSession) {
            try {
                await this.cdpSession.send('Page.stopScreencast');
                await this.cdpSession.detach();
            } catch (error) {
                console.error('CDP会话清理失败:', error);
            }
        }
        
        if (this.page) {
            try {
                await this.page.close();
            } catch (error) {
                console.error('页面关闭失败:', error);
            }
        }
        
        if (this.browser) {
            try {
                await this.browser.close();
            } catch (error) {
                console.error('浏览器关闭失败:', error);
            }
        }
    }
}

const controller = new HeadlessStreamingBrowser();

wss.on('connection', (ws) => {
    const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    controller.addClient(ws, clientId);

    ws.on('message', async (message) => {
        try {
            const data = JSON.parse(message);
            await controller.handleInteraction(data, clientId);
        } catch (error) {
            console.error('消息处理失败:', error);
        }
    });

    ws.on('close', () => {
        controller.removeClient(clientId);
    });

    ws.on('error', (error) => {
        console.error(`客户端 ${clientId} 错误:`, error);
        controller.removeClient(clientId);
    });
});

app.use(cors());
app.use(express.json());

// API端点用于Vue应用调用
app.get('/api/status', (req, res) => {
    res.json({
        status: 'ok',
        initialized: controller.isInitialized,
        clients: controller.clients.size,
        performanceMode: controller.performanceMode
    });
});

app.post('/api/navigate', async (req, res) => {
    try {
        const { url } = req.body;
        if (!url) {
            return res.status(400).json({ error: '缺少URL参数' });
        }
        
        await controller.handleInteraction({ type: 'navigate', url });
        res.json({ success: true, message: '导航成功' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        initialized: controller.isInitialized,
        clients: controller.clients.size,
        performanceMode: controller.performanceMode
    });
});

(async () => {
    try {
        await controller.initialize();
        
        server.listen(port, () => {
            console.log('========================================');
            console.log('无头浏览器远程控制服务已启动');
            console.log(`WebSocket服务: ws://localhost:${port}`);
            console.log(`HTTP API: http://localhost:${port}`);
            console.log(`默认URL: ${defaultURL}`);
            console.log('========================================');
        });
    } catch (error) {
        console.error('服务启动失败:', error);
        process.exit(1);
    }
})();

process.on('SIGINT', async () => {
    console.log('\n正在关闭服务...');
    await controller.cleanup();
    server.close(() => {
        console.log('服务已关闭');
        process.exit(0);
    });
});

process.on('SIGTERM', async () => {
    await controller.cleanup();
    server.close();
    process.exit(0);
});

process.on('uncaughtException', (error) => {
    console.error('未捕获异常:', error);
    controller.cleanup().then(() => {
        process.exit(1);
    });
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('未处理的Promise拒绝:', reason);
});