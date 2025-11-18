document.addEventListener("DOMContentLoaded", () => {
  const addBtn = document.getElementById("add-item-btn");
  const form = document.getElementById("add-item-form");
  const nameInput = document.getElementById("item-name");
  const saveBtn = document.getElementById("save-item-btn");
  const rackTop = document.querySelector(".rack-top");
  const rackBottom = document.querySelector(".rack-bottom");
  const slots = document.querySelectorAll(".slot");

  let addMode = false;
  let selectedSlots = [];
  let currentRackId = new URLSearchParams(window.location.search).get("rack") || "1";


  function setAddMode(on) {
    addMode = on;
    selectedSlots = [];
    slots.forEach(s => s.classList.remove("selected"));
    form.style.display = on ? "block" : "none";
  }

  // Enter selection mode
  addBtn.addEventListener("click", () => {
    setAddMode(true);
    nameInput.focus();
  });

  // Click to select slots only in add
  slots.forEach(slot => {
    slot.addEventListener("click", () => {
      if (!addMode) return;
      const id = slot.dataset.slotId;
      // Prevent selecting already occupied slots (optional UI guard)
      if (slot.classList.contains("occupied")) return;

      slot.classList.toggle("selected");
      if (slot.classList.contains("selected")) {
        selectedSlots.push(id);
      } else {
        selectedSlots = selectedSlots.filter(sid => sid !== id);
      }
    });
  });

  // Save item: create item, then place into selected slots
  saveBtn.addEventListener("click", async () => {
    const label = nameInput.value.trim();
    const tagsRaw = document.getElementById('item-tags').value || '';
    const otherRaw = document.getElementById('item-other-names').value || '';

    // convert comma-separated inputs into arrays (trimmed)
    const tagsArr = tagsRaw.split(',').map(s => s.trim()).filter(Boolean);
    const otherArr = otherRaw.split(',').map(s => s.trim()).filter(Boolean);
    if (!label) {
      alert("Please enter an item name.");
      return;
    }
    if (selectedSlots.length === 0) {
      alert("Please select at least one location on the rack.");
      return;
    }

    try {
      const res = await fetch("/place", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slot_ids: selectedSlots,   // use selectedSlots
          rack_id: currentRackId,    // comes from rack buttons or URL
          label: label,              // item name
          tags: tagsArr,
          other_names: otherArr
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        alert(errData.error || "Failed to place item.");
        return;
      }

      const data = await res.json();
      console.log("Placed:", data);

      alert("Item added and placed.");
      setAddMode(false);
      nameInput.value = "";
      document.getElementById('item-tags').value = '';
      document.getElementById('item-other-names').value = '';
      window.location.reload();
    } catch (e) {
      console.error(e);
      alert("Network error. Please try again.");
    }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".delete-btn").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      const slot = btn.closest(".slot");
      const itemId = slot.dataset.itemId;
      const slotId = slot.dataset.slotId;

      fetch("/remove", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item_id: itemId, slot_id: slotId })
      })
      .then(res => res.json())
      .then(() => window.location.reload());
    });
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const editBtn = document.getElementById("edit-mode-btn");

  editBtn.addEventListener("click", () => {
    const params = new URLSearchParams(window.location.search);
    const inEdit = params.get('edit') === '1';
    // Toggle the edit param but preserve other params (like `rack`)
    if (inEdit) {
      params.delete('edit');
    } else {
      params.set('edit', '1');
    }
    const qs = params.toString();
    window.location.href = qs ? `/?${qs}` : '/';
  });

  // Update button text based on current mode
  if (window.location.search.includes("edit=1")) {
    editBtn.textContent = "Exit Edit Mode";
  } else {
    editBtn.textContent = "Edit Mode";
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const itemNameValue = document.getElementById("item-name-value");
  const locationValue = document.getElementById("location-value");
  const tagsValue = document.getElementById("tags-value");
  const otherNamesValue = document.getElementById("other-names-value");

  document.querySelectorAll(".rack-bottom .slot, .rack-top .slot").forEach(slot => {
    slot.addEventListener("click", () => {
      if (!slot.classList.contains("occupied")) return; // ignore empty slots
      itemNameValue.textContent = slot.dataset.label || "Unnamed Item";
      locationValue.textContent = slot.dataset.location || "N/A";   // ← location numbers
      tagsValue.textContent = slot.dataset.tags || "None";
      otherNamesValue.textContent = slot.dataset.otherNames || "None";

      // also populate the detail panel (if present) and show it
      const detailPanel = document.getElementById('item-details');
      const detailName = document.getElementById('detail-name');
      const detailLocation = document.getElementById('detail-location');
      const detailTags = document.getElementById('detail-tags');
      const detailOther = document.getElementById('detail-other-names');
      if (detailPanel && detailName) {
        detailName.textContent = slot.dataset.label || "Unnamed Item";
        detailLocation.textContent = slot.dataset.location || "N/A";
        detailTags.textContent = slot.dataset.tags || "None";
        detailOther.textContent = slot.dataset.otherNames || "None";
        detailPanel.style.display = 'block';
      }
    });
  });
});

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('.rack-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const rackId = btn.dataset.rack;

      document.querySelectorAll('.rack-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      // Preserve existing query params (notably `edit`) when switching racks
      const params = new URLSearchParams(window.location.search);
      params.set('rack', rackId);
      const qs = params.toString();
      window.location = `/?${qs}`;
    });
  });

  // Highlight the current rack button on page load based on the URL param
  const params = new URLSearchParams(window.location.search);
  const initial = params.get('rack') || '1';
  const sel = document.querySelector(`.rack-btn[data-rack="${initial}"]`);
  if (sel) {
    document.querySelectorAll('.rack-btn').forEach(b => b.classList.remove('active'));
    sel.classList.add('active');
  }
});
