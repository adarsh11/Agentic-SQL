document.addEventListener('DOMContentLoaded', () => {
    const queryInput = document.getElementById('queryInput');
    const generateBtn = document.getElementById('generateBtn');
    const resultSection = document.getElementById('resultSection');
    const errorSection = document.getElementById('errorSection');
    const statusBadge = document.getElementById('statusBadge');

    // Dropdown and Logs
    const suggestionSelect = document.getElementById('suggestionSelect');
    const agentLogs = document.getElementById('agentLogs');
    const toggleLogsBtn = document.getElementById('toggleLogsBtn');
    const closeLogsBtn = document.getElementById('closeLogsBtn');

    // Output Elements
    const sqlOutput = document.getElementById('sqlOutput');
    const categoryLabel = document.getElementById('categoryLabel');
    const accuracyLabel = document.getElementById('accuracyLabel');
    const plannerReasoning = document.getElementById('plannerReasoning');
    const toolOrder = document.getElementById('toolOrder');
    const attemptsLabel = document.getElementById('attemptsLabel');
    const evaluationFeedback = document.getElementById('evaluationFeedback');
    const optimizationList = document.getElementById('optimizationList');
    const errorMessage = document.getElementById('errorMessage');

    // Schema Modal Elements
    const viewSchemaBtn = document.getElementById('viewSchemaBtn');
    const schemaModal = document.getElementById('schemaModal');
    const closeSchemaBtn = document.getElementById('closeSchemaBtn');
    const schemaContent = document.getElementById('schemaContent');
    const schemaTabs = document.querySelectorAll('.schema-tab');

    // Backend URL Configuration
    const LOCAL_BASE = 'http://127.0.0.1:8000';


    const BASE_URL = LOCAL_BASE;

    const API_URL = `${BASE_URL}/generate-sql`;
    const HEALTH_URL = `${BASE_URL}/health`;
    const SCHEMA_URL = `${BASE_URL}/schema`;

    let schemaData = null;

    // Check Health on Load
    async function checkHealth() {
        try {
            const response = await fetch(HEALTH_URL);
            const data = await response.json();
            if (data.status === 'healthy') {
                console.log('✅ Backend is healthy');
                statusBadge.textContent = 'Connected';
                statusBadge.className = 'badge success';
            }
        } catch (err) {
            console.error('❌ Backend connection failed');
            statusBadge.textContent = 'Disconnected';
            statusBadge.className = 'badge loading'; // Using loading style for error
            statusBadge.style.color = 'var(--error)';
        }
    }

    checkHealth();

    // Handle Generation
    async function generateSql() {
        const query = queryInput.value.trim();
        if (!query) return;

        // Reset and Show Loading State
        setLoadingState(true);
        errorSection.classList.add('hidden');
        resultSection.classList.add('hidden');
        agentLogs.classList.add('hidden');
        toggleLogsBtn.classList.remove('active');

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    verbose: true
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Server responded with an error');
            }

            const data = await response.json();

            // Always display result/traces if we got data back
            displayResult(data);

            if (!data.success) {
                showError(data.error || 'The system was unable to generate a valid SQL query for this request.');
                // Automatically show logs on failure to show traces
                agentLogs.classList.remove('hidden');
                toggleLogsBtn.classList.add('active');
            }

        } catch (error) {
            console.error('API Error:', error);
            showError('Could not connect to the backend server. Make sure the FastAPI backend is running on port 127.0.0.1:8000.');
        } finally {
            setLoadingState(false);
        }
    }

    function setLoadingState(isLoading) {
        if (isLoading) {
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<span>Processing...</span><i class="fas fa-circle-notch fa-spin"></i>';
        } else {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<span>Generate SQL</span><i class="fas fa-paper-plane"></i>';
        }
    }

    function displayResult(data) {
        // Show result section
        resultSection.classList.remove('hidden');

        // Update Status Badge
        if (data.success) {
            statusBadge.textContent = 'Complete';
            statusBadge.className = 'badge success';
        } else {
            statusBadge.textContent = 'Failed';
            statusBadge.className = 'badge loading'; // Re-using styling
            statusBadge.style.background = 'rgba(239, 68, 68, 0.1)';
            statusBadge.style.color = 'var(--error)';
            statusBadge.style.border = '1px solid rgba(239, 68, 68, 0.3)';
        }

        // Update basic info
        sqlOutput.textContent = data.sql || '-- No SQL generated for this request.';
        categoryLabel.textContent = data.category || 'N/A';
        accuracyLabel.textContent = data.evaluation?.accuracy_score !== undefined
            ? `${Math.round(data.evaluation.accuracy_score * 100)}%`
            : '0%';

        // Update Planner Trace
        plannerReasoning.textContent = data.planner_reasoning || 'Query analysis complete.';
        toolOrder.innerHTML = '';
        if (data.tool_order && data.tool_order.length > 0) {
            data.tool_order.forEach(tool => {
                const span = document.createElement('span');
                span.className = 'tool-tag';
                span.textContent = tool;
                toolOrder.appendChild(span);
            });
        } else {
            toolOrder.innerHTML = '<span class="tag-placeholder">Standard execution path taken</span>';
        }

        // Update Generator Trace
        attemptsLabel.textContent = data.attempts || 1;

        // Update Evaluator Trace
        evaluationFeedback.textContent = data.evaluation?.feedback || 'Query validated and approved by the Evaluation Agent.';

        // Update optimization suggestions
        optimizationList.innerHTML = '';
        const suggestions = data.evaluation?.suggestions || [];
        if (suggestions.length > 0) {
            suggestions.forEach(suggestion => {
                const li = document.createElement('li');
                li.textContent = suggestion;
                optimizationList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.textContent = 'Query is already highly optimized.';
            optimizationList.appendChild(li);
        }

        // Update agent logs with SQL history and tool calls
        updateAgentLogsWithHistory(data);

        // Scroll into view
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function showError(msg) {
        errorSection.classList.remove('hidden');
        errorMessage.textContent = msg;
        errorSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Toggle Logs Logic
    function toggleLogs() {
        const isHidden = agentLogs.classList.toggle('hidden');
        toggleLogsBtn.classList.toggle('active', !isHidden);
        if (!isHidden) {
            agentLogs.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    toggleLogsBtn.addEventListener('click', toggleLogs);
    closeLogsBtn.addEventListener('click', () => {
        agentLogs.classList.add('hidden');
        toggleLogsBtn.classList.remove('active');
    });

    // Suggestion Dropdown Logic
    suggestionSelect.addEventListener('change', () => {
        if (suggestionSelect.value) {
            queryInput.value = suggestionSelect.value;
            generateSql();
        }
    });

    // Event Listeners
    generateBtn.addEventListener('click', generateSql);

    queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            generateSql();
        }
    });

    // Copy SQL
    document.getElementById('copySqlBtn').addEventListener('click', () => {
        const sql = sqlOutput.textContent;
        navigator.clipboard.writeText(sql).then(() => {
            const btn = document.getElementById('copySqlBtn');
            const icon = btn.querySelector('i');
            icon.className = 'fas fa-check';
            btn.style.color = 'var(--success)';
            setTimeout(() => {
                icon.className = 'fas fa-copy';
                btn.style.color = 'var(--text-muted)';
            }, 2000);
        });
    });

    // Schema Viewer Functions
    async function loadSchema() {
        try {
            const response = await fetch(SCHEMA_URL);
            schemaData = await response.json();
            displaySchema(0); // Show first category by default
        } catch (error) {
            console.error('Failed to load schema:', error);
            schemaContent.innerHTML = '<p class="loading-text">Failed to load schema data.</p>';
        }
    }

    function displaySchema(categoryIndex) {
        if (!schemaData || !schemaData.categories[categoryIndex]) return;

        const category = schemaData.categories[categoryIndex];
        let html = '';

        category.tables.forEach(table => {
            html += `
                <div class="schema-table">
                    <h3>${table.table_name}</h3>
                    <p>${table.description}</p>
                    <div class="schema-columns">
                        ${table.columns.map(col => {
                const isKey = table.key_columns.includes(col);
                return `<div class="schema-column ${isKey ? 'key' : ''}">${col}${isKey ? ' 🔑' : ''}</div>`;
            }).join('')}
                    </div>
                </div>
            `;
        });

        schemaContent.innerHTML = html;
    }

    // Schema Modal Event Listeners
    viewSchemaBtn.addEventListener('click', (e) => {
        e.preventDefault();
        schemaModal.classList.remove('hidden');
        if (!schemaData) {
            loadSchema();
        }
    });

    closeSchemaBtn.addEventListener('click', () => {
        schemaModal.classList.add('hidden');
    });

    schemaModal.addEventListener('click', (e) => {
        if (e.target === schemaModal) {
            schemaModal.classList.add('hidden');
        }
    });

    schemaTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            schemaTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const categoryIndex = parseInt(tab.dataset.category);
            displaySchema(categoryIndex);
        });
    });

    // Update logs display to show SQL history and tool calls
    function updateAgentLogsWithHistory(data) {
        // Update planner with tool calls
        if (data.tool_calls_made && data.tool_calls_made.planner) {
            const toolCallsHtml = data.tool_calls_made.planner.map(tc =>
                `<span class="tool-tag">${tc}</span>`
            ).join('');
            if (toolCallsHtml) {
                document.getElementById('toolOrder').innerHTML = toolCallsHtml;
            }
        }

        // Update generator with SQL history
        if (data.sql_history && data.sql_history.length > 0) {
            const generatorBody = document.querySelector('.log-entry.generator .log-body');
            let historyHtml = '<p>Query generation completed.</p>';
            historyHtml += `<div class="attempts-count">Total Attempts: <span>${data.sql_history.length}</span></div>`;

            if (data.sql_history.length > 1) {
                historyHtml += '<details style="margin-top: 0.75rem;"><summary style="cursor: pointer; color: var(--accent);">View All SQL Attempts</summary>';
                data.sql_history.forEach((sql, index) => {
                    historyHtml += `<div style="margin-top: 0.5rem; padding: 0.5rem; background: rgba(0,0,0,0.2); border-radius: 6px;">
                        <strong>Attempt ${index + 1}:</strong>
                        <pre style="font-size: 0.75rem; margin-top: 0.25rem; overflow-x: auto;">${sql}</pre>
                    </div>`;
                });
                historyHtml += '</details>';
            }

            generatorBody.innerHTML = historyHtml;
        }
    }
});
