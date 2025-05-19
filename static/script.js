let task = null;
let timerEnd = null;
let interval = null;
let battleInterval = null;
let prevPlayerHealth = null;
let prevMonsterHealth = null;

function loadState() {
  fetch("/state")
    .then(res => res.json())
    .then(data => {
      updateStatButtons(data);
      updateHealthBars(data);
      updateGold(data.gold);
      updateEquipment(data.equipment);

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
      if (data.quest) {
        document.getElementById("questText").textContent =
          `Train ${data.quest.stat} ${data.quest.goal} times`;
        document.getElementById("questProgress").textContent =
          `Progress: ${data.quest.progress} / ${data.quest.goal}`;
        document.getElementById("questReward").textContent =
          `Reward: ${data.quest.reward} gold`;

        const now = Date.now() / 1000;
        const secondsLeft = Math.max(0, 86400 - (now - data.quest.created_at));
        const hrs = Math.floor(secondsLeft / 3600);
        const mins = Math.floor((secondsLeft % 3600) / 60);
        const secs = Math.floor(secondsLeft % 60);
        document.getElementById("questTimeLeft").textContent =
          `Refreshes in: ${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
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

  document.getElementById("playerHealthText").textContent = `${data.health} / ${data.max_health}`;
  document.getElementById("monsterHealthText").textContent = `${data.monster_health} / ${data.monster_max}`;

  const playerSprite = document.getElementById("playerSprite");
  const monsterSprite = document.getElementById("monsterSprite");

  if (prevPlayerHealth !== null && data.health < prevPlayerHealth) {
    const dmg = prevPlayerHealth - data.health;
    triggerDamageAnimation(playerSprite);
    showFloatingDamage("playerEntity", dmg);
  }

  if (prevMonsterHealth !== null && data.monster_health < prevMonsterHealth) {
    const dmg = prevMonsterHealth - data.monster_health;
    triggerDamageAnimation(monsterSprite);
    showFloatingDamage("monsterEntity", dmg);
  }

  prevPlayerHealth = data.health;
  prevMonsterHealth = data.monster_health;
}

function updateEquipment(equipment) {
  ['weapon', 'armor', 'accessory'].forEach(slot => {
    const el = document.querySelector(`#slot-${slot} span`);
    el.textContent = equipment[slot] || 'None';
  });
}

function triggerDamageAnimation(element) {
  element.classList.remove("sprite-hit");
  void element.offsetWidth; // reflow to restart animation
  element.classList.add("sprite-hit");
}

function showFloatingDamage(entityId, amount) {
  const container = document.getElementById(entityId);
  const float = document.createElement("div");
  float.className = "floating-damage";
  float.textContent = `-${amount}`;

  float.style.left = `${Math.random() * 60 + 20}px`; // random offset
  container.appendChild(float);

  setTimeout(() => {
    float.remove();
  }, 1000);
}

function doBattle() {
  fetch("/battle", {
    method: "POST"
  }).then(() => loadState());
}
function loadShop() {
  fetch("/shop")
    .then(res => res.json())
    .then(items => {
      const shopDiv = document.getElementById("shop");
      shopDiv.innerHTML = "";
      items.forEach(item => {
        const el = document.createElement("div");
        el.className = "shop-item";
        el.innerHTML = `
          <img src="/static/icons/${item.icon}" alt="${item.name}" class="shop-icon">
          <div>
            <strong>${item.name}</strong><br>
            <small>${item.description}</small><br>
            <button onclick="buyItem(${item.id}, ${item.cost})">Buy (${item.cost}g)</button>
          </div>
        `;
        shopDiv.appendChild(el);
      });
    });
}

function buyItem(itemId, cost) {
  fetch("/buy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_id: itemId })
  })
  .then(res => res.json())
  .then(data => {
    alert(data.message);
    loadState();
    loadShop();
  });
}

function addGold() {
  fetch("/add-gold", {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  }).then(() => loadState());
}

window.onload = () => {
  loadState();
  loadShop();
};
