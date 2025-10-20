function submitEntry() {
  const item = document.getElementById("item").value;
  const rack = document.getElementById("rack").value;
  const location = document.getElementById("location").value;

  fetch("/add_entry", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item, rack, location })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      alert("Entry added!");
      addToList(item);
    } else {
      alert("Failed to add entry.");
    }
  });
}

function addToList(item) {
  const list = document.getElementById("itemList");
  if (!document.getElementById(item)) {
    const li = document.createElement("li");
    li.textContent = item;
    li.id = item;
    list.appendChild(li);
  }
}


function highlightItem(item) {
  const el = document.getElementById(item);
  if (el) {
    el.classList.add("highlight");
    setTimeout(() => el.classList.remove("highlight"), 5000);
  }
}

function pollHighlights() {
  setInterval(() => {
    fetch("/get_highlights")
      .then(res => res.json())
      .then(data => {
        data.items.forEach(item => highlightItem(item));
      });
  }, 1000); // Poll every second
}

function highlightItem(item) {
  const el = document.getElementById(item);
  if (el) {
    el.classList.add("highlight");
    setTimeout(() => el.classList.remove("highlight"), 5000);
  }
}

window.onload = pollHighlights;
