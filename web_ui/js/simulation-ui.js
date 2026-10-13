class SimulationUI {
    constructor() {
        this.canvas = document.getElementById('map-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.tooltip = document.getElementById('tooltip');
        
        // Simulation data
        this.worldData = null;
        this.agents = [];
        this.selectedAgent = null;
        this.selectedTile = null;
        
        // UI state
        this.autoRefresh = false;
        this.refreshInterval = null;
        this.scale = 1;
        this.offsetX = 0;
        this.offsetY = 0;
        this.cellSize = 8;
        
        // WebSocket for real-time updates
        this.ws = null;
        this.wsUrl = 'ws://localhost:8765';
        
        // Terrain colors
        this.terrainColors = {
            'MOUNTAIN': '#8B4513',
            'FOREST': '#228B22',
            'GRASSLAND': '#32CD32',
            'WATER': '#1E90FF',
            'DESERT': '#F4A460',
            'PLAINS': '#90EE90',
            'SWAMP': '#556B2F',
            'TUNDRA': '#708090'
        };
        
        // Resource colors
        this.resourceColors = {
            'wood': '#8B4513',
            'stone': '#696969',
            'water': '#1E90FF',
            'food': '#FFD700',
            'metal': '#C0C0C0',
            'fruit': '#FF6347'
        };
        
        this.initialize();
    }
    
    initialize() {
        this.setupCanvas();
        this.setupEventListeners();
        this.loadSimulationData();
        this.connectWebSocket();
    }
    
    setupCanvas() {
        const container = this.canvas.parentElement;
        this.canvas.width = container.clientWidth;
        this.canvas.height = container.clientHeight;
        
        // Handle window resize
        window.addEventListener('resize', () => {
            this.canvas.width = container.clientWidth;
            this.canvas.height = container.clientHeight;
            this.draw();
        });
    }
    
    setupEventListeners() {
        // Canvas interactions
        this.canvas.addEventListener('click', (e) => this.handleCanvasClick(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleCanvasMouseMove(e));
        this.canvas.addEventListener('wheel', (e) => this.handleCanvasWheel(e));
        this.canvas.addEventListener('mouseleave', () => this.hideTooltip());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            switch(e.key) {
                case 'r': case 'R':
                    this.refreshData();
                    break;
                case ' ':
                    e.preventDefault();
                    this.toggleAutoRefresh();
                    break;
                case 'Escape':
                    this.clearSelection();
                    break;
            }
        });
    }
    
    handleCanvasClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Convert screen coordinates to world coordinates
        const worldX = Math.floor((x - this.offsetX) / (this.cellSize * this.scale));
        const worldY = Math.floor((y - this.offsetY) / (this.cellSize * this.scale));
        
        // Check if clicked on agent
        const clickedAgent = this.agents.find(agent => 
            Math.floor(agent.x) === worldX && Math.floor(agent.y) === worldY
        );
        
        if (clickedAgent) {
            this.selectAgent(clickedAgent);
        } else {
            this.selectTile(worldX, worldY);
        }
        
        this.draw();
    }
    
    handleCanvasMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const worldX = Math.floor((x - this.offsetX) / (this.cellSize * this.scale));
        const worldY = Math.floor((y - this.offsetY) / (this.cellSize * this.scale));
        
        // Show tooltip with tile/agent info
        this.showTooltip(e, worldX, worldY);
    }
    
    handleCanvasWheel(e) {
        e.preventDefault();
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
        const newScale = Math.max(0.5, Math.min(5, this.scale * zoomFactor));
        
        // Zoom towards mouse position
        this.offsetX = mouseX - (mouseX - this.offsetX) * (newScale / this.scale);
        this.offsetY = mouseY - (mouseY - this.offsetY) * (newScale / this.scale);
        this.scale = newScale;
        
        this.draw();
    }
    
    showTooltip(e, worldX, worldY) {
        if (!this.worldData || worldX < 0 || worldY < 0 || 
            worldX >= this.worldData.size || worldY >= this.worldData.size) {
            this.hideTooltip();
            return;
        }
        
        // Check for agent at position
        const agent = this.agents.find(a => 
            Math.floor(a.x) === worldX && Math.floor(a.y) === worldY
        );
        
        let content = '';
        if (agent) {
            content = `<strong>${agent.name}</strong><br>`;
            content += `ID: ${agent.aid}<br>`;
            content += `Position: (${worldX}, ${worldY})<br>`;
            content += `Health: ${agent.health || 100}<br>`;
            if (agent.current_action) {
                content += `Action: ${agent.current_action}`;
            }
        } else {
            // Show tile info
            const tileIndex = worldY * this.worldData.size + worldX;
            const terrain = this.worldData.terrain[tileIndex];
            const resources = this.worldData.resources[tileIndex] || {};
            
            content = `<strong>Tile (${worldX}, ${worldY})</strong><br>`;
            content += `Terrain: ${terrain}<br>`;
            
            const resourceList = Object.entries(resources)
                .filter(([_, count]) => count > 0)
                .map(([type, count]) => `${type}: ${count}`)
                .join(', ');
            
            if (resourceList) {
                content += `Resources: ${resourceList}`;
            } else {
                content += 'No resources';
            }
        }
        
        this.tooltip.innerHTML = content;
        this.tooltip.style.display = 'block';
        this.tooltip.style.left = e.pageX + 10 + 'px';
        this.tooltip.style.top = e.pageY + 10 + 'px';
    }
    
    hideTooltip() {
        this.tooltip.style.display = 'none';
    }
    
    selectAgent(agent) {
        this.selectedAgent = agent;
        this.selectedTile = null;
        this.updateAgentInfo(agent);
        this.highlightAgentInList(agent.aid);
    }
    
    selectTile(x, y) {
        if (!this.worldData || x < 0 || y < 0 || 
            x >= this.worldData.size || y >= this.worldData.size) {
            return;
        }
        
        this.selectedAgent = null;
        this.selectedTile = { x, y };
        this.updateTileInfo(x, y);
    }
    
    clearSelection() {
        this.selectedAgent = null;
        this.selectedTile = null;
        document.getElementById('selected-agent-info').innerHTML = 
            '<p style="color: #888; text-align: center; margin: 20px 0;">Click on an agent to view details</p>';
        document.getElementById('selected-tile-info').innerHTML = 
            '<p style="color: #888; text-align: center; margin: 20px 0;">Click on the map to view tile details</p>';
        this.draw();
    }
    
    updateAgentInfo(agent) {
        const container = document.getElementById('selected-agent-info');
        
        let html = `
            <div class="info-item">
                <label>Name:</label>
                <span>${agent.name}</span>
            </div>
            <div class="info-item">
                <label>ID:</label>
                <span>${agent.aid}</span>
            </div>
            <div class="info-item">
                <label>Position:</label>
                <span>(${Math.floor(agent.x)}, ${Math.floor(agent.y)})</span>
            </div>
            <div class="info-item">
                <label>Health:</label>
                <span>${agent.health || 100}</span>
            </div>
        `;
        
        if (agent.current_action) {
            html += `
                <div class="info-item">
                    <label>Current Action:</label>
                    <span>${agent.current_action}</span>
                </div>
            `;
        }
        
        if (agent.group_id) {
            html += `
                <div class="info-item">
                    <label>Group:</label>
                    <span>${agent.group_id}</span>
                </div>
            `;
        }
        
        // Inventory
        if (agent.inventory && Object.keys(agent.inventory).length > 0) {
            html += '<h4 style="margin: 15px 0 10px 0; color: #4CAF50;">Inventory</h4>';
            html += '<div class="resource-grid">';
            for (const [item, count] of Object.entries(agent.inventory)) {
                if (count > 0) {
                    html += `
                        <div class="resource-item">
                            <span class="count">${count}</span>
                            <span>${item}</span>
                        </div>
                    `;
                }
            }
            html += '</div>';
        }
        
        // Skills
        if (agent.skills && Object.keys(agent.skills).length > 0) {
            html += '<h4 style="margin: 15px 0 10px 0; color: #4CAF50;">Skills</h4>';
            html += '<div class="skills-list">';
            for (const [skill, level] of Object.entries(agent.skills)) {
                html += `<span class="skill-tag">${skill} (${level})</span>`;
            }
            html += '</div>';
        }
        
        // Social connections
        if (agent.social_connections && agent.social_connections.length > 0) {
            html += '<h4 style="margin: 15px 0 10px 0; color: #4CAF50;">Social Connections</h4>';
            agent.social_connections.slice(0, 5).forEach(conn => {
                html += `
                    <div class="info-item">
                        <label>${conn.name}:</label>
                        <span>${conn.relationship || 'Acquaintance'}</span>
                    </div>
                `;
            });
        }
        
        container.innerHTML = html;
    }
    
    updateTileInfo(x, y) {
        const container = document.getElementById('selected-tile-info');
        const tileIndex = y * this.worldData.size + x;
        const terrain = this.worldData.terrain[tileIndex];
        const resources = this.worldData.resources[tileIndex] || {};
        
        let html = `
            <div class="info-item">
                <label>Position:</label>
                <span>(${x}, ${y})</span>
            </div>
            <div class="info-item">
                <label>Terrain:</label>
                <span>${terrain}</span>
            </div>
        `;
        
        // Resources
        const resourceEntries = Object.entries(resources).filter(([_, count]) => count > 0);
        if (resourceEntries.length > 0) {
            html += '<h4 style="margin: 15px 0 10px 0; color: #4CAF50;">Resources</h4>';
            html += '<div class="resource-grid">';
            resourceEntries.forEach(([type, count]) => {
                html += `
                    <div class="resource-item">
                        <span class="count">${count}</span>
                        <span>${type}</span>
                    </div>
                `;
            });
            html += '</div>';
        } else {
            html += `
                <div class="info-item">
                    <label>Resources:</label>
                    <span>None</span>
                </div>
            `;
        }
        
        // Agents on this tile
        const agentsOnTile = this.agents.filter(agent => 
            Math.floor(agent.x) === x && Math.floor(agent.y) === y
        );
        
        if (agentsOnTile.length > 0) {
            html += '<h4 style="margin: 15px 0 10px 0; color: #4CAF50;">Agents Here</h4>';
            agentsOnTile.forEach(agent => {
                html += `
                    <div class="info-item">
                        <label>${agent.name}:</label>
                        <span>${agent.current_action || 'Idle'}</span>
                    </div>
                `;
            });
        }
        
        container.innerHTML = html;
    }
    
    highlightAgentInList(agentId) {
        document.querySelectorAll('.agent-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        const selectedItem = document.querySelector(`[data-agent-id="${agentId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
            selectedItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
    
    draw() {
        if (!this.worldData) return;
        
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        const scaledCellSize = this.cellSize * this.scale;
        const size = this.worldData.size;
        
        // Draw terrain
        for (let y = 0; y < size; y++) {
            for (let x = 0; x < size; x++) {
                const screenX = this.offsetX + x * scaledCellSize;
                const screenY = this.offsetY + y * scaledCellSize;
                
                // Skip if outside canvas
                if (screenX + scaledCellSize < 0 || screenY + scaledCellSize < 0 ||
                    screenX > this.canvas.width || screenY > this.canvas.height) {
                    continue;
                }
                
                const tileIndex = y * size + x;
                const terrain = this.worldData.terrain[tileIndex];
                const resources = this.worldData.resources[tileIndex] || {};
                
                // Draw terrain
                this.ctx.fillStyle = this.terrainColors[terrain] || '#666';
                this.ctx.fillRect(screenX, screenY, scaledCellSize, scaledCellSize);
                
                // Draw resources as small dots
                if (scaledCellSize > 4) {
                    const resourceEntries = Object.entries(resources).filter(([_, count]) => count > 0);
                    resourceEntries.slice(0, 4).forEach(([type, count], index) => {
                        const dotSize = Math.max(2, scaledCellSize * 0.15);
                        const dotX = screenX + (index % 2) * (scaledCellSize * 0.5) + dotSize;
                        const dotY = screenY + Math.floor(index / 2) * (scaledCellSize * 0.5) + dotSize;
                        
                        this.ctx.fillStyle = this.resourceColors[type] || '#FFD700';
                        this.ctx.beginPath();
                        this.ctx.arc(dotX, dotY, dotSize, 0, 2 * Math.PI);
                        this.ctx.fill();
                    });
                }
                
                // Highlight selected tile
                if (this.selectedTile && this.selectedTile.x === x && this.selectedTile.y === y) {
                    this.ctx.strokeStyle = '#FFD700';
                    this.ctx.lineWidth = 2;
                    this.ctx.strokeRect(screenX, screenY, scaledCellSize, scaledCellSize);
                }
            }
        }
        
        // Draw grid if zoomed in enough
        if (scaledCellSize > 10) {
            this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
            this.ctx.lineWidth = 1;
            this.ctx.beginPath();
            
            for (let x = 0; x <= size; x++) {
                const screenX = this.offsetX + x * scaledCellSize;
                this.ctx.moveTo(screenX, this.offsetY);
                this.ctx.lineTo(screenX, this.offsetY + size * scaledCellSize);
            }
            
            for (let y = 0; y <= size; y++) {
                const screenY = this.offsetY + y * scaledCellSize;
                this.ctx.moveTo(this.offsetX, screenY);
                this.ctx.lineTo(this.offsetX + size * scaledCellSize, screenY);
            }
            
            this.ctx.stroke();
        }
        
        // Draw agents
        this.agents.forEach(agent => {
            const screenX = this.offsetX + agent.x * scaledCellSize;
            const screenY = this.offsetY + agent.y * scaledCellSize;
            
            // Skip if outside canvas
            if (screenX < -scaledCellSize || screenY < -scaledCellSize ||
                screenX > this.canvas.width || screenY > this.canvas.height) {
                return;
            }
            
            const agentSize = Math.max(4, scaledCellSize * 0.6);
            
            // Agent circle
            this.ctx.fillStyle = this.selectedAgent && this.selectedAgent.aid === agent.aid ? 
                '#FFD700' : '#FF6B6B';
            this.ctx.beginPath();
            this.ctx.arc(
                screenX + scaledCellSize / 2, 
                screenY + scaledCellSize / 2, 
                agentSize / 2, 
                0, 2 * Math.PI
            );
            this.ctx.fill();
            
            // Agent border
            this.ctx.strokeStyle = '#000';
            this.ctx.lineWidth = 1;
            this.ctx.stroke();
            
            // Agent name (if zoomed in enough)
            if (scaledCellSize > 20) {
                this.ctx.fillStyle = '#fff';
                this.ctx.font = `${Math.max(8, scaledCellSize * 0.2)}px Arial`;
                this.ctx.textAlign = 'center';
                this.ctx.fillText(
                    agent.name, 
                    screenX + scaledCellSize / 2, 
                    screenY + scaledCellSize + 12
                );
            }
        });
    }
    
    async loadSimulationData() {
        try {
            document.getElementById('loading').style.display = 'block';
            
            // Try to load from the latest output file first
            const response = await fetch('/api/simulation-data');
            if (response.ok) {
                const data = await response.json();
                this.updateSimulationData(data);
            } else {
                // Fallback to sample data
                await this.loadSampleData();
            }
        } catch (error) {
            console.error('Error loading simulation data:', error);
            await this.loadSampleData();
        } finally {
            document.getElementById('loading').style.display = 'none';
        }
    }
    
    async loadSampleData() {
        // Generate sample data for demonstration
        const size = 32;
        const terrainTypes = ['MOUNTAIN', 'FOREST', 'GRASSLAND', 'WATER', 'DESERT'];
        const resourceTypes = ['wood', 'stone', 'water', 'food'];
        
        this.worldData = {
            size: size,
            terrain: [],
            resources: []
        };
        
        // Generate terrain
        for (let i = 0; i < size * size; i++) {
            this.worldData.terrain.push(
                terrainTypes[Math.floor(Math.random() * terrainTypes.length)]
            );
            
            // Generate resources
            const resources = {};
            if (Math.random() < 0.3) {
                const resourceType = resourceTypes[Math.floor(Math.random() * resourceTypes.length)];
                resources[resourceType] = Math.floor(Math.random() * 5) + 1;
            }
            this.worldData.resources.push(resources);
        }
        
        // Generate sample agents
        this.agents = [];
        for (let i = 0; i < 8; i++) {
            this.agents.push({
                aid: i,
                name: `Agent${i}`,
                x: Math.random() * size,
                y: Math.random() * size,
                health: 100,
                current_action: ['foraging', 'exploring', 'resting', 'crafting'][Math.floor(Math.random() * 4)],
                inventory: {
                    wood: Math.floor(Math.random() * 10),
                    stone: Math.floor(Math.random() * 5),
                    food: Math.floor(Math.random() * 8)
                },
                skills: {
                    foraging: Math.floor(Math.random() * 5) + 1,
                    crafting: Math.floor(Math.random() * 3) + 1
                }
            });
        }
        
        this.updateUI();
        this.draw();
    }
    
    updateSimulationData(data) {
        this.worldData = data.world;
        this.agents = data.agents || [];
        this.updateUI();
        this.draw();
    }
    
    updateUI() {
        // Update status panel
        document.getElementById('current-turn').textContent = this.worldData.turn || 0;
        document.getElementById('agent-count').textContent = this.agents.length;
        document.getElementById('group-count').textContent = 
            new Set(this.agents.filter(a => a.group_id).map(a => a.group_id)).size;
        document.getElementById('current-era').textContent = this.worldData.era || 'Stone Age';
        
        // Update agent list
        this.updateAgentList();
        
        // Update world stats
        this.updateWorldStats();
    }
    
    updateAgentList() {
        const container = document.getElementById('agent-list');
        
        let html = '';
        this.agents.forEach(agent => {
            html += `
                <div class="agent-item" data-agent-id="${agent.aid}" onclick="ui.selectAgentFromList(${agent.aid})">
                    <div class="agent-name">${agent.name}</div>
                    <div class="agent-details">
                        Position: (${Math.floor(agent.x)}, ${Math.floor(agent.y)}) | 
                        Action: ${agent.current_action || 'Idle'}
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    updateWorldStats() {
        const container = document.getElementById('world-stats');
        
        if (!this.worldData) return;
        
        // Calculate terrain distribution
        const terrainCounts = {};
        this.worldData.terrain.forEach(terrain => {
            terrainCounts[terrain] = (terrainCounts[terrain] || 0) + 1;
        });
        
        // Calculate total resources
        const resourceCounts = {};
        this.worldData.resources.forEach(tileResources => {
            Object.entries(tileResources).forEach(([type, count]) => {
                resourceCounts[type] = (resourceCounts[type] || 0) + count;
            });
        });
        
        let html = '<h4 style="margin-bottom: 10px; color: #4CAF50;">Terrain Distribution</h4>';
        Object.entries(terrainCounts).forEach(([terrain, count]) => {
            const percentage = ((count / (this.worldData.size * this.worldData.size)) * 100).toFixed(1);
            html += `
                <div class="info-item">
                    <label>${terrain}:</label>
                    <span>${percentage}%</span>
                </div>
            `;
        });
        
        html += '<h4 style="margin: 15px 0 10px 0; color: #4CAF50;">Total Resources</h4>';
        Object.entries(resourceCounts).forEach(([type, count]) => {
            html += `
                <div class="info-item">
                    <label>${type}:</label>
                    <span>${count}</span>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    selectAgentFromList(agentId) {
        const agent = this.agents.find(a => a.aid === agentId);
        if (agent) {
            this.selectAgent(agent);
            this.centerOnAgent(agent);
            this.draw();
        }
    }
    
    centerOnAgent(agent) {
        const scaledCellSize = this.cellSize * this.scale;
        this.offsetX = this.canvas.width / 2 - agent.x * scaledCellSize;
        this.offsetY = this.canvas.height / 2 - agent.y * scaledCellSize;
    }
    
    connectWebSocket() {
        try {
            this.ws = new WebSocket(this.wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                document.getElementById('connection-status').classList.add('connected');
                document.getElementById('connection-text').textContent = 'Connected';
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                document.getElementById('connection-status').classList.remove('connected');
                document.getElementById('connection-text').textContent = 'Disconnected';
                
                // Try to reconnect after 5 seconds
                setTimeout(() => this.connectWebSocket(), 5000);
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
        }
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'simulation_update':
                this.updateSimulationData(data.data);
                break;
            case 'agent_update':
                this.updateAgent(data.data);
                break;
            case 'log_entry':
                this.addLogEntry(data.data);
                break;
        }
    }
    
    updateAgent(agentData) {
        const index = this.agents.findIndex(a => a.aid === agentData.aid);
        if (index !== -1) {
            this.agents[index] = agentData;
        } else {
            this.agents.push(agentData);
        }
        
        if (this.selectedAgent && this.selectedAgent.aid === agentData.aid) {
            this.selectedAgent = agentData;
            this.updateAgentInfo(agentData);
        }
        
        this.updateAgentList();
        this.draw();
    }
    
    addLogEntry(logData) {
        const container = document.getElementById('log-container');
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        const timestamp = new Date(logData.timestamp).toLocaleTimeString();
        entry.innerHTML = `
            <span class="log-timestamp">${timestamp}</span>
            <span class="log-level-${logData.level.toLowerCase()}">${logData.message}</span>
        `;
        
        container.appendChild(entry);
        container.scrollTop = container.scrollHeight;
        
        // Keep only last 100 entries
        while (container.children.length > 100) {
            container.removeChild(container.firstChild);
        }
    }
}

// Global UI instance
let ui;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    ui = new SimulationUI();
});

// Tab switching
function switchTab(tabName) {
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// Control functions
function refreshData() {
    if (ui) {
        ui.loadSimulationData();
    }
}

function toggleAutoRefresh() {
    if (!ui) return;
    
    ui.autoRefresh = !ui.autoRefresh;
    const btn = document.getElementById('auto-refresh-btn');
    
    if (ui.autoRefresh) {
        btn.textContent = '⏸️ Auto';
        ui.refreshInterval = setInterval(() => ui.loadSimulationData(), 5000);
    } else {
        btn.textContent = '▶️ Auto';
        if (ui.refreshInterval) {
            clearInterval(ui.refreshInterval);
            ui.refreshInterval = null;
        }
    }
}

function exportData() {
    if (!ui || !ui.worldData) return;
    
    const data = {
        world: ui.worldData,
        agents: ui.agents,
        timestamp: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `simulation_export_${new Date().toISOString().slice(0, 19)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    URL.revokeObjectURL(url);
}

function resetView() {
    if (!ui) return;
    
    ui.scale = 1;
    ui.offsetX = 0;
    ui.offsetY = 0;
    ui.draw();
}