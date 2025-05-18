let task = null;
let timerEnd = null;
let interval = null;
let battleInterval = null;

function loadState() {
  fetch("/state")
    .then(res => res.json())
    .then(data => {
      updateStatButtons(data);
      updateHealthBars(data);
      updateGold(data.gold);

      if (data.current_stat && data.task_start > 0) {
        task = data.current_stat;
        timerEnd = data.task_start * 1000 + 25 * 60 * 1000;
        document.getElementById("levelingStatus").textContent =
          `Leveling up ${capitalize(task)}...`;
        document.getElementById("progressContainer").style.display = "block";
        disableButtons(true);
        interval = setInterval(updateTimer, 1000);
        updateTimer();
      } else {
        disableButtons(false);
      }

      if (!battleInterval) {
        battleInterval = setInterval(doBattle, 2000);
      }
    });
}

function startTask(stat) {
  if (task) return;
  task = stat;
  timerEnd = Date.now() + 25 * 60 * 1000;

  fetch("/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stat: stat })
  });

  document.getElementById("levelingStatus").textContent = `Leveling up ${capitalize(stat)}...`;
  document.getElementById("progressContainer").style.display = "block";
  disableButtons(true);

  interval = setInterval(updateTimer, 1000);
  updateTimer();
}

function updateTimer() {
  const timeLeft = timerEnd - Date.now();
  const total = 25 * 60 * 1000;
  const percent = Math.max(0, Math.min(100, 100 - (timeLeft / total) * 100));
  document.getElementById("progressBar").style.width = `${percent}%`;

  if (timeLeft <= 0) {
    clearInterval(interval);
    document.getElementById("timerDisplay").textContent = "";
    document.getElementById("confirmModal").style.display = "flex";
    return;
  }

  const min = Math.floor(timeLeft / 60000);
  const sec = Math.floor((timeLeft % 60000) / 1000);
  document.getElementById("timerDisplay").textContent = `⏳ Time left: ${min}:${sec.toString().padStart(2, '0')}`;
}

function completeTask(success) {
  fetch("/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ success: success })
  }).then(() => {
    document.getElementById("confirmModal").style.display = "none";
    task = null;
    document.getElementById("levelingStatus").textContent = "";
    document.getElementById("progressContainer").style.display = "none";
    document.getElementById("progressBar").style.width = "0%";
    disableButtons(false);
    loadState();
  });
}

function disableButtons(state) {
  document.querySelectorAll(".actions button").forEach(btn => {
    btn.disabled = state;
  });
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function updateStatButtons(data) {
  document.getElementById("btn-strength").textContent = `💪 Strength (${data.strength})`;
  document.getElementById("btn-intelligence").textContent = `🧠 Intelligence (${data.intelligence})`;
  document.getElementById("btn-vitality").textContent = `❤️ Vitality (${data.vitality})`;
  document.getElementById("btn-charisma").textContent = `😎 Charisma (${data.charisma})`;
}

function updateGold(gold) {
  document.getElementById("goldDisplay").textContent = `Gold: ${gold}`;
}

function updateHealthBars(data) {
  const playerPercent = (data.health / data.max_health) * 100;
  const monsterPercent = (data.monster_health / data.monster_max) * 100;
  document.getElementById("playerHealthBar").style.width = `${playerPercent}%`;
  document.getElementById("monsterHealthBar").style.width = `${monsterPercent}%`;
}

function doBattle() {
  fetch("/battle", {
    method: "POST"
  }).then(() => loadState());
}

window.onload = loadState;
