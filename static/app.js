let currentItemId = null;
let selectedSlots = new Set();

document.getElementById("place-item")?.addEventListener("click", async () => {
  if (!currentItemId || selectedSlots.size === 0) return;
  const res = await fetch("/place", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_id: currentItemId, slot_ids: Array.from(selectedSlots) }),
  });
  const data = await res.json();
  if (data.ok) {
    // Update location label with the first slot chosen
    const firstSlot = Array.from(selectedSlots)[0];
    const labelEl = document.getElementById("location-label");
    if (labelEl) {
      labelEl.textContent = `Location: ${firstSlot}`;
    }
    location.reload();
  } else {
    alert(data.error || "Failed");
  }
});


document.querySelectorAll(".slot").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (!currentItemId) return;
    if (btn.classList.contains("occupied")) {
      alert("Slot occupied");
      return;
    }
    const sid = parseInt(btn.dataset.slotId, 10);
    if (selectedSlots.has(sid)) {
      selectedSlots.delete(sid);
      btn.classList.remove("selected");
    } else {
      selectedSlots.add(sid);
      btn.classList.add("selected");
    }
  });
});

document.getElementById("place-item")?.addEventListener("click", async () => {
  if (!currentItemId || selectedSlots.size === 0) return;
  const res = await fetch("/place", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_id: currentItemId, slot_ids: Array.from(selectedSlots) }),
  });
  const data = await res.json();
  if (data.ok) {
    location.reload();
  } else {
    alert(data.error || "Failed");
  }
});
