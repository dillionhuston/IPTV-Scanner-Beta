let currentPage = 1;

// Reference to the loading bar
const loadingBar = document.getElementById('loadingBar');
const channelsList = document.getElementById('channels');

// Show loading bar
function showLoading() {
    loadingBar.classList.add('active');
    channelsList.style.opacity = '0.5';
    channelsList.setAttribute('aria-busy', 'true');
}

// Hide loading bar
function hideLoading() {
    loadingBar.classList.remove('active');
    channelsList.style.opacity = '1';
    channelsList.setAttribute('aria-busy', 'false');
}

// Display error message
function showError(message) {
    channelsList.innerHTML = `<div class="error-message">${message}</div>`;
    hideLoading();
}

document.getElementById('search').addEventListener('input', (e) => {
    const query = e.target.value;
    if (query.length > 2) {
        searchChannels(query);
    } else {
        loadChannels(currentPage);
    }
});

function loadChannels(page) {
    showLoading();
    fetch(`/channels?page=${page}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch channels');
            }
            return response.json();
        })
        .then(data => {
            renderChannels(data);
            renderPagination(page);
            hideLoading();
        })
        .catch(error => {
            showError('Error loading channels. Please try again.');
            console.error(error);
        });
}

function searchChannels(query) {
    showLoading();
    fetch(`/search?query=${query}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to search channels');
            }
            return response.json();
        })
        .then(data => {
            renderChannels(data);
            hideLoading();
        })
        .catch(error => {
            showError('Error searching channels. Please try again.');
            console.error(error);
        });
}

function renderChannels(channels) {
    const channelsDiv = document.getElementById('channels');
    channelsDiv.innerHTML = channels.map(channel => `
        <div class="channel">
            <div class="name">${channel.name}</div>
            <div class="playing-now">${channel.playing_now}</div>
            <div class="actions">
                <button onclick="copyStream('${channel.url}')"><i class="fas fa-copy"></i> Copy</button>
                <button onclick="openStream('${channel.url}')"><i class="fas fa-external-link-alt"></i> Open</button>
                <button onclick="openInBrowser('${channel.url}')"><i class="fas fa-globe"></i> Browser</button>
            </div>
        </div>
    `).join('');
}

function renderPagination(page) {
    const paginationDiv = document.querySelector('.pagination');
    paginationDiv.querySelector('#pageInfo').textContent = `Page ${page}`;
    paginationDiv.querySelector('#prevPage').disabled = page === 1;
}

function changePage(page) {
    if (page < 1) return;
    currentPage = page;
    loadChannels(page);
}

function copyStream(url) {
    navigator.clipboard.writeText(url).then(() => {
        alert('Stream URL copied to clipboard!');
    });
}

function openStream(url) {
    window.open(`vlc://${url}`, '_blank');
}

function openInBrowser(url) {
    window.open(url, '_blank');
}

// Initialize
loadChannels(currentPage);