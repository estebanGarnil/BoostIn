const csrftoken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

PROCHAINE_EXECUTION = document.getElementById('prochaine_connexion');

// GRAPHIQUES 
// #######################################################################
function debounceFunction() {
  let timeout;

  return function(date) {
    const executeFunction = () => {
      console.log(date)

      fetch('https://boostin.scrooge.finance/campagnes/stat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({'date' : date})
      })
    .then(response => response.json())
    .then(data => {
        if (nbCon != null) {
          donnees_stat_con = data.stat_con;
          nbCon.data.datasets[0].data = donnees_stat_con;
          nbCon.update();
        }
        if (nbMess != null) {
          donnees_stat_mes = data.stat_mes;
          nbMess.data.datasets[0].data = donnees_stat_mes;
          nbMess.update();  
        }

    })
    .catch(error => {
      console.error('Une erreur est survenue:', error); // Gérer les erreurs éventuelles
    });    

    };

    // Si un timeout existe, l'annuler
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(executeFunction, 1500);
  };
}

const tempo = debounceFunction();

document.addEventListener('DOMContentLoaded', function() {
  const currentDate = new Date();

  // Calculer la différence en jours
  const timeDiff = currentDate - startDate;
  const daysDiff = Math.floor(timeDiff / (1000 * 3600 * 24));

  // Fonction pour formater la date
  function formatDate(date) {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
}

    console.log(donnees_stat_mes);
    console.log(donnees_stat_con);
    // graphique nb connexion
    const data = {
        labels: [
          'accepté',
          'en attente',
          'non demandé',
          'succès',
          'refusé'
        ],
        datasets: [{
          data: [donnees_stat_con.ACC, donnees_stat_con.ATT, donnees_stat_con.NENV, donnees_stat_con.REF, donnees_stat_con.SUC],
          backgroundColor: [
            'rgb(67, 56, 202)',
            'rgb(165, 180, 252)',
            'rgb(224, 231, 255)',
            'rgb(49, 46, 129)',
            'rgb(55, 48, 163)'
          ],
          hoverOffset: 4
        }]
      };
      
    const config = {
        type: 'doughnut',
        data: data,
      };
    
      
    const nbCon = new Chart(document.getElementById('nombre-connexion'), config);

    // graphique nb message
    const data_message = {
        labels: [
          '1er message',
          '2eme message',
          '3eme message',
          'pas encore envoyé'
        ],
        datasets: [{
          data: [donnees_stat_mes.M1ST, donnees_stat_mes.M2ND, donnees_stat_mes.M3RD, donnees_stat_mes.NENV],
          backgroundColor: [
            'rgb(199, 210, 254)',
            'rgb(165, 180, 252)',
            'rgb(129, 140, 248)',
            'rgb(224, 231, 255)'
          ],
          hoverOffset: 4
        }]
      };
      
    const config_message = {
        type: 'doughnut',
        data: data_message,
      };
    
            
    const nbMess = new Chart(document.getElementById('nombre-message'), config_message);
    window.nbCon = nbCon;
    window.nbMess = nbMess;

    //   ------------------


});
// #######################################################################


function attendre(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// async function waiting_loading(url) {
//   var etatapp = true;

//   while (etatapp) { // Boucle infinie, à adapter selon tes besoins
//       await attendre(5000); // Attendre 5 secondes avant de recommencer
//       fetch('https://boostin.scrooge.finance/campagnes/loading/', {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//             'X-CSRFToken': csrftoken
//         },
//         body: JSON.stringify({})
//       })
//       .then(response => {
//           // Si tu veux voir le statut HTTP avant de parser en JSON
//           console.log('HTTP Status:', response.status);
//           return response.json();
//       })
//       .then(data => {
//           if (data.status === 'success') {
//             console.log('Status dans la réponse JSON:', data.status);
//             location.reload(true);
//             etatapp = false;
//           }
//       })
//       .catch(error => {
//           console.error('Il y a eu un problème avec la requête fetch:', error);
//       });
//   }
// }

// Appel de la fonction avec l'URL désirée
    


function start() {
    var checkbox = document.getElementById("startbutton");

    var loader = document.getElementById("loader");
    var switchLabel = checkbox.parentNode;
  
    if (checkbox.checked) {
        // Cache le switch et montre le loader
        switchLabel.style.display = "none";
        loader.classList.remove("hidden");
    }
      // dans la fonction fetch -> attendre que le programme se soit bien lancé    

    if (checkbox.checked) {
        fetch('https://boostin.scrooge.finance/campagnes/a/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
          console.log(data.suivi_channel)
            if (data.suivi_channel == 'started') {
                var checkbox = document.getElementById("startbutton");
                checkbox.checked = true;
                checkbox.disabled = false;
            }
            else if (data.status == 'error') {
              var checkbox = document.getElementById("startbutton");
              checkbox.disabled = true;
            }
        })

    } else {

        fetch('https://boostin.scrooge.finance/campagnes/a/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({})
        })
        .then(response => {
            // location.reload(true);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .catch(error => {
            console.error('Il y a eu un problème avec la requête fetch:', error);
        });
    }
}

// Fonction pour démarrer le processus
function startProcess() {
  fetch('https://boostin.scrooge.finance/campagnes/a/start', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
      },
      body: JSON.stringify({})
  })
  .then(response => {
      if (!response.ok) {
          throw new Error('Network response was not ok');
      }
      return response.json(); // Extraction de la réponse JSON
  })
  .then(data => {
      if (data.suivi_channel) {
          const canal = data.suivi_channel; // Assigner le canal à partir de la réponse JSON
          const eventSource = new EventSource(`https://boostin.scrooge.finance/campagnes/sse/${canal}`);
          console.log("ecoute du canal");

          let currentStep = 0;

          function startSteps() {
          const steps = document.querySelectorAll(".step");
          const stepLines = document.querySelectorAll(".step-line");
  
          // Si une étape précédente existe, marquer comme "complétée"
          if (currentStep > 0) {
              steps[currentStep - 1]?.classList.remove("bg-blue-500"); // Enlever l'état actif
              steps[currentStep - 1]?.classList.add("bg-green-500"); // Marquer comme complétée
              stepLines[currentStep - 1]?.classList.replace("bg-gray-300", "bg-green-500"); // Ligne complétée
          }
  
          // Si une étape suivante existe, marquer comme "en cours"
          if (currentStep < steps.length) {
              steps[currentStep]?.classList.replace("bg-gray-300", "bg-blue-500"); // Étape en cours
              currentStep++; // Passer à l'étape suivante
          } else {
              console.log("Toutes les étapes sont terminées !");
          }
          }
          document.getElementById("updates").textContent = "Attribution des horaires d'execution";
          startSteps();

          // Gestion des messages SSE
          eventSource.onmessage = (event) => {
                const data_mess = JSON.parse(event.data); // Convertir le message en JSON
                const messageData = JSON.parse(data_mess.data);
                console.log("Mise à jour reçue : ", messageData);

                // Exemple : Affichage d'une description si disponible
                if (messageData.description && messageData.etape === "info") {
                  prochaine_execution = document.getElementById('prochaine_connexion');
                  prochaine_execution.textContent = messageData.description;
                }
                else if (messageData.description) {
                    document.getElementById("updates").textContent = messageData.description;
                }

                // Avancer dans les étapes si nécessaire
                if (messageData.etape) {
                  if (messageData.etape === "suivant") {
                      startSteps();
                      console.log('startsteps');
                  }

                  // Arrêter le flux SSE si un message 'stop' est reçu
                  if (messageData.etape === "echec") {
                      console.log("Processus terminé : ", messageData);
                      eventSource.close();
                  }
                  if (messageData.etape === "arret") {
                    console.log("Processus terminé : ", messageData);
                    startSteps();
                    eventSource.close();
                    hideLoadingPopup();
                    location.reload(true);
                  }
                }

          };

          // Gestion des erreurs SSE
          eventSource.onerror = (error) => {
            console.error("Erreur SSE : ", error);
            eventSource.close();
          };
      
      } else {
          console.error("Attribut 'suivi_channel' manquant dans la réponse JSON");
      }
  })
  .catch(error => {
      console.error('Il y a eu un problème avec la requête fetch:', error);
  });
}

// Appeler la fonction pour démarrer le processus

document.addEventListener("DOMContentLoaded", () => {

  console.log('attente bouton');

  const toggleButton = document.getElementById("toggle-button");
  const toggleLabel = document.getElementById("toggle-label");
  let isActive = false;

  
  if (toggleLabel.textContent == 'On') {
    isActive = true;
  } 
  console.log(isActive);

  toggleButton.addEventListener("click", () => {
    isActive = !isActive;

    if (isActive) {
      toggleButton.classList.replace("bg-gray-300", "bg-indigo-500");
      toggleButton.firstElementChild.classList.add("translate-x-5");
      toggleLabel.textContent = "On";

      showLoadingPopup();

      startProcess();
      
    } else {
      toggleButton.classList.replace("bg-indigo-500", "bg-gray-300");
      toggleButton.firstElementChild.classList.remove("translate-x-5");
      toggleLabel.textContent = "Off";

      document.getElementById('prochaine_connexion').textContent = "None";

      fetch('https://boostin.scrooge.finance/campagnes/a/stop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({})
      })
      .then(response => {
          if (!response.ok) {
              throw new Error('Network response was not ok');
          }
          return response.json();
      })
      .catch(error => {
          console.error('Il y a eu un problème avec la requête fetch:', error);
      });

    }
  });
});

// popup 
function showLoadingPopup() {
  document.getElementById('loadingPopup').classList.remove('hidden');
}

function hideLoadingPopup() {
  document.getElementById('loadingPopup').classList.add('hidden');
}

function loadSomething() {
  showLoadingPopup(); // Affiche le popup

}

// document.addEventListener('DOMContentLoaded', function () {
//   document.getElementById('toggle-button').addEventListener('click', loadSomething);
// });
