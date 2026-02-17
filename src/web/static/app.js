const API_URL = '/api';

document.addEventListener('DOMContentLoaded', () => {
    fetchStats();
    fetchItems(5, 'overview-feed'); // Initial overview items
    fetchItems(50, 'full-feed');
    fetchTrends();
    fetchBriefings();

    // Tab Switching
    document.querySelectorAll('.nav-links li').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.nav-links li').forEach(l => l.classList.remove('active'));
            document.querySelectorAll('.view-section').forEach(s => s.style.display = 'none');

            item.classList.add('active');
            const tabId = item.getAttribute('data-tab');
            document.getElementById(`view-${tabId}`).style.display = 'block';
        });
    });

    // Refresh Button
    document.getElementById('refresh-btn').addEventListener('click', async () => {
        const btn = document.getElementById('refresh-btn');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning...';
        btn.disabled = true;

        try {
            await fetch(`${API_URL}/scan`, { method: 'POST' });
            alert('Scan completed!');
            location.reload();
        } catch (e) {
            console.error(e);
            alert('Scan failed');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    // Filters
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const cat = btn.getAttribute('data-cat');
            fetchItems(50, 'full-feed', cat === 'all' ? null : cat);
        });
    });
});

async function fetchStats() {
    const res = await fetch(`${API_URL}/stats`);
    const data = await res.json();
    document.getElementById('count-sources').innerText = data.sources;
    document.getElementById('count-items').innerText = data.items;
    document.getElementById('count-trends').innerText = data.trends;
}

async function fetchItems(limit, containerId, category = null) {
    let url = `${API_URL}/items?limit=${limit}`;
    if (category) url += `&category=${category}`;

    const res = await fetch(url);
    const items = await res.json();
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'feed-item';
        card.innerHTML = `
            <div class="meta">
                <span class="tag">${item.category || 'General'}</span>
                <span>${new Date(item.published_date).toLocaleDateString()}</span>
            </div>
            <h4><a href="${item.url}" target="_blank" style="color:white;text-decoration:none;">${item.title}</a></h4>
            <div class="meta">
                <span>Score: ${item.relevance_score || 'N/A'}</span>
            </div>
            <p>${item.content ? item.content.substring(0, 150) + '...' : 'No content preview'}</p>
        `;
        container.appendChild(card);
    });
}

async function fetchTrends() {
    const res = await fetch(`${API_URL}/trends`);
    const trends = await res.json();
    const container = document.getElementById('trends-grid');
    container.innerHTML = '';

    if (trends.length === 0) {
        container.innerHTML = '<p style="color:var(--text-secondary)">No trends detected yet.</p>';
        return;
    }

    trends.forEach(trend => {
        const card = document.createElement('div');
        card.className = 'trend-card';
        card.innerHTML = `
            <div class="trend-header">
                <h3>${trend.trend_name}</h3>
                <span class="strength-badge strength-${trend.strength}">${trend.strength}</span>
            </div>
            <p style="margin-bottom:1rem;color:var(--text-secondary)">${trend.implications_for_thesis || 'No analysis available'}</p>
            <div class="meta">
                <span>Confidence: ${trend.confidence}</span>
            </div>
        `;
        container.appendChild(card);
    });
}

async function fetchBriefings() {
    const res = await fetch(`${API_URL}/briefings`);
    const briefings = await res.json();
    const container = document.getElementById('briefing-content');

    if (briefings.length === 0) {
        container.innerHTML = '<p>No briefings generated yet.</p>';
        return;
    }

    const b = briefings[0]; // Show latest
    container.innerHTML = `
        <div class="feed-item" style="border-left: 4px solid var(--accent-purple)">
            <h3>Briefing: Week of ${b.week_starting}</h3>
            <h4 style="margin-top:1rem">Executive Summary</h4>
            <p>${b.executive_summary}</p>
            
            <h4 style="margin-top:1rem">Action Items</h4>
            <ul>
                ${(b.action_items || []).map(i => `<li>${i}</li>`).join('')}
            </ul>
        </div>
    `;
}
