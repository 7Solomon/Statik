import * as Data from './structureData.js';
// --- UI Toggles ---

window.toggleFileDrawer = () => {
    const drawer = document.getElementById('file-drawer');
    const backdrop = document.getElementById('file-drawer-backdrop');
    const isClosed = drawer.classList.contains('translate-x-full');

    if (isClosed) {
        // Open
        drawer.classList.remove('translate-x-full');
        backdrop.classList.remove('hidden');
        refreshFileList(); // Fetch list when opening
    } else {
        // Close
        drawer.classList.add('translate-x-full');
        backdrop.classList.add('hidden');
    }
};

// --- API Interactions ---

window.handleSave = async () => {
    const nameInput = document.getElementById('save-name-input');
    const name = nameInput.value.trim();

    if (!name) {
        alert("Please enter a system name");
        return;
    }

    const systemData = Data.getExportData(); // Use your existing export function

    try {
        const res = await fetch('/analyze/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, system: systemData })
        });

        if (res.ok) {
            nameInput.value = ''; // Clear input
            refreshFileList();    // Reload list
            // Optional: Show success toast
        } else {
            alert("Failed to save system");
        }
    } catch (e) {
        console.error(e);
        alert("Error saving system");
    }
};

async function refreshFileList() {
    const container = document.getElementById('file-list-container');
    const loader = document.getElementById('file-list-loader');

    container.innerHTML = '';
    loader.classList.remove('hidden');

    try {
        const res = await fetch('/analyze/list');
        const files = await res.json();

        loader.classList.add('hidden');

        if (files.length === 0) {
            container.innerHTML = '<div class="text-xs text-slate-400 text-center py-4">No saved systems found.</div>';
            return;
        }

        files.forEach(file => {
            const item = document.createElement('div');
            item.className = "group bg-white p-3 rounded-lg border border-slate-200 hover:border-blue-300 transition-all shadow-sm flex flex-col gap-2";
            item.innerHTML = `
                <div class="flex justify-between items-start">
                    <div>
                        <div class="font-semibold text-slate-700 text-sm">${file.name}</div>
                        <div class="text-[10px] text-slate-400 font-mono mt-0.5">${formatDate(file.saved_at)}</div>
                    </div>
                </div>
                <div class="flex gap-2 mt-1 opacity-60 group-hover:opacity-100 transition-opacity">
                    <button onclick="loadSystemBySlug('${file.slug}')" 
                        class="flex-1 bg-indigo-50 text-indigo-600 hover:bg-indigo-100 py-1.5 rounded text-xs font-medium transition-colors">
                        Load
                    </button>
                    <button onclick="deleteSystemBySlug('${file.slug}')" 
                        class="px-3 bg-red-50 text-red-600 hover:bg-red-100 py-1.5 rounded text-xs font-medium transition-colors">
                        Delete
                    </button>
                </div>
            `;
            container.appendChild(item);
        });

    } catch (e) {
        console.error(e);
        loader.innerText = "Error loading files.";
    }
}
window.loadSystemBySlug = async (slug) => {
    if (!confirm("Load system? Unsaved changes will be lost.")) return;

    try {
        const res = await fetch(`/analyze/load/${slug}`);
        if (!res.ok) throw new Error("Load failed");

        const data = await res.json();

        const systemData = data.system || data;

        if (Data.loadSystem) {
            Data.loadSystem(systemData);

            if (window.triggerRender) {
                window.triggerRender();
            } else {
                console.warn("triggerRender not found on window");
            }

            // Close the drawer
            window.toggleFileDrawer();
        } else {
            console.error("Data.loadSystem is not defined");
        }

    } catch (e) {
        console.error(e);
        alert("Could not load system");
    }
};

window.deleteSystemBySlug = async (slug) => {
    if (!confirm("Are you sure you want to delete this system?")) return;

    try {
        const res = await fetch(`/analyze/delete/${slug}`, { method: 'DELETE' });
        if (res.ok) {
            refreshFileList();
        } else {
            alert("Delete failed");
        }
    } catch (e) {
        console.error(e);
    }
};

function formatDate(isoString) {
    const d = new Date(isoString);
    return d.toLocaleDateString('de-DE') + ' ' + d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
}
