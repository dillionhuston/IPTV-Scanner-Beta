let currentPage = 1;

document.getElementById('search').addEventListener('input', (e) => {
    const query = e.target.value;
    if (query.length > 2) {
        searchChannels(query);
    } else {
        loadChannels(currentPage);
    }
});

function loadChannels(page) {
    fetch(`/channels?page=${page}`)
        .then(response => response.json())
        .then(data => {
            renderChannels(data);
            renderPagination(page);
        });
}

function searchChannels(query) {
    fetch(`/search?query=${query}`)
        .then(response => response.json())
        .then(data => renderChannels(data));
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