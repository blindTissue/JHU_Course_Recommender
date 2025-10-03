// Course Recommender Frontend Logic

let currentResults = [];
let currentQuery = '';

document.addEventListener('DOMContentLoaded', function() {
    const searchBtn = document.getElementById('search-btn');
    const queryInput = document.getElementById('query');
    const loadingDiv = document.getElementById('loading');
    const resultsDiv = document.getElementById('results');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const getSummaryBtn = document.getElementById('get-summary-btn');
    const chatInput = document.getElementById('chat-input');

    searchBtn.addEventListener('click', performSearch);
    chatSendBtn.addEventListener('click', sendChatMessage);
    getSummaryBtn.addEventListener('click', getSummary);

    // Allow Enter key in textarea (Ctrl+Enter to submit)
    queryInput.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            performSearch();
        }
    });

    async function performSearch() {
        const query = queryInput.value.trim();

        if (!query) {
            alert('Please enter what you would like to learn');
            return;
        }

        // Get filter values
        const filters = {};
        const school = document.getElementById('school').value;
        const department = document.getElementById('department').value;
        const level = document.getElementById('level').value;

        if (school) filters.SchoolName = school;
        if (department) filters.Department = department;
        if (level) filters.Level = level;

        const top_k = parseInt(document.getElementById('top_k').value);

        // Show loading, hide results
        loadingDiv.style.display = 'block';
        resultsDiv.innerHTML = '';
        searchBtn.disabled = true;

        try {
            const response = await fetch('/recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    filters: filters,
                    top_k: top_k
                })
            });

            const data = await response.json();

            if (data.success) {
                currentResults = data.results;
                currentQuery = query;
                displayResults(data.results);

                // Show chatbot section
                document.getElementById('chatbot-section').style.display = 'block';
                document.getElementById('chat-messages').innerHTML = '';
            } else {
                alert('Error: ' + (data.error || 'Unknown error occurred'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to get recommendations. Please try again.');
        } finally {
            loadingDiv.style.display = 'none';
            searchBtn.disabled = false;
        }
    }

    function convertMarkdownToHTML(markdown) {
        let html = markdown;

        // Headers
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Italic
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Lists
        html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
        html = html.replace(/^- (.*$)/gim, '<li>$1</li>');
        html = html.replace(/^\d+\. (.*$)/gim, '<li>$1</li>');

        // Wrap consecutive list items in ul/ol tags
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

        // Line breaks
        html = html.replace(/\n\n/g, '</p><p>');
        html = html.replace(/\n/g, '<br>');

        // Wrap in paragraph if not already wrapped
        if (!html.startsWith('<')) {
            html = '<p>' + html + '</p>';
        }

        return html;
    }

    async function sendChatMessage() {
        const chatInput = document.getElementById('chat-input');
        const message = chatInput.value.trim();

        if (!message) {
            alert('Please enter a question');
            return;
        }

        await sendToClaude(message);
        chatInput.value = '';
    }

    async function getSummary() {
        await sendToClaude('');
    }

    async function sendToClaude(userMessage) {
        const chatMessages = document.getElementById('chat-messages');
        const chatSendBtn = document.getElementById('chat-send-btn');
        const getSummaryBtn = document.getElementById('get-summary-btn');

        // Add user message if provided
        if (userMessage) {
            const userMsgDiv = document.createElement('div');
            userMsgDiv.className = 'chat-message user';
            userMsgDiv.textContent = userMessage;
            chatMessages.appendChild(userMsgDiv);
        }

        // Create assistant message container for streaming
        const assistantMsgDiv = document.createElement('div');
        assistantMsgDiv.className = 'chat-message assistant';
        assistantMsgDiv.textContent = '▋'; // Show typing cursor
        chatMessages.appendChild(assistantMsgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        chatSendBtn.disabled = true;
        getSummaryBtn.disabled = true;

        let fullResponse = '';

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_query: currentQuery,
                    courses: currentResults,
                    message: userMessage
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const {done, value} = await reader.read();

                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.error) {
                                assistantMsgDiv.textContent = 'Error: ' + data.error;
                                break;
                            }

                            if (data.text) {
                                fullResponse += data.text;
                                assistantMsgDiv.innerHTML = convertMarkdownToHTML(fullResponse) + '<span class="cursor">▋</span>';
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            }

                            if (data.done) {
                                // Remove cursor when done
                                assistantMsgDiv.innerHTML = convertMarkdownToHTML(fullResponse);
                            }
                        } catch (e) {
                            // Skip invalid JSON
                        }
                    }
                }
            }

            chatMessages.scrollTop = chatMessages.scrollHeight;
        } catch (error) {
            console.error('Error:', error);
            assistantMsgDiv.textContent = 'Failed to get response from Claude. Please try again.';
        } finally {
            chatSendBtn.disabled = false;
            getSummaryBtn.disabled = false;
        }
    }

    function displayResults(results) {
        if (results.length === 0) {
            resultsDiv.innerHTML = '<p style="text-align: center; padding: 40px;">No courses found matching your criteria.</p>';
            return;
        }

        let html = `
            <div class="result-header">
                <h2>Found ${results.length} Recommended Courses</h2>
            </div>
        `;

        results.forEach((course, index) => {
            html += `
                <div class="course-card">
                    <div class="course-header">
                        <div class="course-title">
                            <h3>${index + 1}. ${course.title}</h3>
                            <span class="course-code">${course.offering_name} - Section ${course.section}</span>
                        </div>
                        <div class="score-badge">
                            Score: ${course.combined_score.toFixed(3)}
                        </div>
                    </div>

                    <div class="course-meta">
                        <div class="meta-item">
                            <span class="meta-label">School:</span> ${course.school}
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Department:</span> ${course.department}
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Instructor:</span> ${course.instructor}
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Level:</span> ${course.level}
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Credits:</span> ${course.credits}
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Status:</span> ${course.status}
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Seats:</span> ${course.seats}
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Time:</span> ${course.meetings}
                        </div>
                    </div>

                    <div class="course-description">
                        ${course.description}
                    </div>

                    <div class="score-breakdown">
                        <span>🔍 BM25: ${course.bm25_score.toFixed(3)}</span>
                        <span>🧠 Embedding: ${course.embedding_score.toFixed(3)}</span>
                        ${course.areas !== 'N/A' && course.areas !== 'None' ? `<span>📚 Areas: ${course.areas}</span>` : ''}
                    </div>
                </div>
            `;
        });

        resultsDiv.innerHTML = html;
    }
});
