// const csrftoken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

let currentPage = 0;
let itemsPerPage = 10;
let tableData = []; // Déclarée en dehors pour être accessible globalement
let filteredData = []; // Contient les données filtrées

function renderTable(data) {
    const tbody = document.querySelector("#dynamicTable tbody");
    tbody.innerHTML = ""; // Efface les anciennes lignes

    const start = currentPage * itemsPerPage;
    const end = start + itemsPerPage;
    const pageData = data.slice(start, end); // Récupère les lignes pour la page actuelle

    pageData.forEach(row => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-gray-50";
        tr.innerHTML = `
            <td class="border px-4 py-2">${row.name}</td>
            <td class="border px-4 py-2"><a href="${row.linkedin_profile}" class="text-indigo-500" target="_blank">${row.linkedin_profile}</a></td>
            <td class="border px-4 py-2">${row.statutes__statutes}</td>
            <td class="border px-4 py-2">
                <button class="delete-btn text-red-500 px-2 py-1 rounded hover:bg-red-100">
                    <svg class="h-5 w-5 inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 6h18M9 6v12M15 6v12M19 6l-1 14H6L5 6m4-2h6M5 6h14"></path>
                    </svg>
                </button>
            </td>
        `;
        tbody.appendChild(tr);

        // Ajoute un gestionnaire d'événement au bouton
        const deleteButton = tr.querySelector(".delete-btn");
        deleteButton.addEventListener("click", () => {
            fetch(`https://boostin.scrooge.finance/campagnes/d/prospect/${row.id}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
            })
            .then(response => {
                console.log(response); // Affiche la réponse brute
                if (response.ok) {
                    tr.remove();
                } else {
                    return response.text().then(text => {
                        console.error("Erreur réponse :", text); // Affiche le contenu brut
                    });
                }
            })
            .catch(error => {
                console.error("Erreur lors de la suppression :", error);
            });
        });
    });

    updateCurrentPage(); // Met à jour la page actuelle
}

function updateCurrentPage() {
    const currentPageElement = document.getElementById("currentPage");
    currentPageElement.textContent = `Page ${currentPage + 1}`;
}

function filterByStatus() {
    const statusFilter = document.getElementById("statusFilter").value;
    if (statusFilter) {
        filteredData = tableData.filter(row => row.statutes__statutes.toString() === statusFilter);
    } else {
        filteredData = tableData; // Affiche toutes les données si aucun filtre sélectionné
    }
    currentPage = 0; // Réinitialiser à la première page après un filtre
    renderTable(filteredData);
}

function updateRowsPerPage() {
    const rowsPerPage = document.getElementById("rowsPerPage").value;
    itemsPerPage = parseInt(rowsPerPage, 10);
    currentPage = 0; // Réinitialiser à la première page
    renderTable(filteredData);
}


function nextPage() {
    if ((currentPage + 1) * itemsPerPage < tableData.length) {
        currentPage++;
        renderTable(filteredData);
    }
}

function previousPage() {
    if (currentPage > 0) {
        currentPage--;
        renderTable(filteredData);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    try {
        const dataElement = document.getElementById('prospectData');

        tableData = JSON.parse(dataElement.textContent); // Récupérer et parser les données
        
        filteredData = tableData;
        renderTable(filteredData); // Appeler la fonction pour remplir le tableau
    } catch (e) {
        console.error("Erreur lors de l'analyse JSON :", e);
    }
});

document.getElementById("statusFilter").addEventListener("change", filterByStatus);
document.getElementById("rowsPerPage").addEventListener("change", updateRowsPerPage);
