// Course Recommender Frontend Logic

document.addEventListener('DOMContentLoaded', function() {
    const searchBtn = document.getElementById('search-btn');
    const queryInput = document.getElementById('query');
    const loadingDiv = document.getElementById('loading');
    const resultsDiv = document.getElementById('results');

    searchBtn.addEventListener('click', performSearch);

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
                displayResults(data.results);
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
            const prerequisites = course.prerequisites && course.prerequisites.length > 0
                ? `<div class="prerequisites">
                     <strong>Prerequisites:</strong>
                     <p>${course.prerequisites[0]}</p>
                   </div>`
                : '';

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

                    ${prerequisites}

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
