document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const addBtn = document.getElementById('add-item-btn');
  const form = document.getElementById('add-item-form');
  const nameInput = document.getElementById('item-name');
  const saveBtn = document.getElementById('save-item-btn');
  const cancelBtn = document.getElementById('cancel-add');
  const slots = Array.from(document.querySelectorAll('.slot'));
  const presetBtns = Array.from(document.querySelectorAll('.preset-tag'));
  const selectedTagsContainer = document.getElementById('selected-tags');
  const customInput = document.getElementById('custom-tag-input');
  const addCustomBtn = document.getElementById('add-custom-tag');
  const otherNamesInput = document.getElementById('item-other-names');
  const swatches = Array.from(document.querySelectorAll('.color-swatch'));
  const widthInput = document.getElementById('item-width');
  const widthIncrease = document.getElementById('width-increase');
  const widthDecrease = document.getElementById('width-decrease');

  // State
  let addMode = false;
  let selectedSlots = [];
  let selectedTags = [];
  let selectedColor = null;
  let itemWidth = 1;
  const params = new URLSearchParams(window.location.search);
  let currentRackId = params.get('rack') || '1';
  
  // Helper to get per-rack config storage key
  function getConfigStorageKey(rackId) {
    return `rackConfig_v1_${rackId}`;
  }
  
  // Safe localStorage get/set with error handling
  function getSavedConfig(rackId) {
    try {
      return localStorage.getItem(getConfigStorageKey(rackId));
    } catch (e) {
      console.warn('localStorage.getItem failed:', e);
      return null;
    }
  }
  
  function setSavedConfig(rackId, config) {
    try {
      localStorage.setItem(getConfigStorageKey(rackId), config);
    } catch (e) {
      console.warn('localStorage.setItem failed:', e);
    }
  }
  
  // Load config from localStorage for this rack, or use URL param, or default to 4x4
  let currentConfig = getSavedConfig(currentRackId) || params.get('config') || '4x4';

  // Helpers
  function setAddMode(on) {
    addMode = on;
    if (!on) {
      // clear selection and form
      selectedSlots = [];
      slots.forEach(s => s.classList.remove('selected'));
      selectedTags = [];
      renderSelectedTags();
      nameInput.value = '';
      otherNamesInput.value = '';
      swatches.forEach(s => s.classList.remove('selected'));
      selectedColor = null;
      itemWidth = 1;
      if (widthInput) widthInput.value = '1';
      form.style.display = 'none';
    } else {
      form.style.display = 'block';
      nameInput.focus();
      // default first swatch
      if (swatches.length) {
        selectSwatch(swatches[0]);
      }
      if (widthInput && !widthInput.value) widthInput.value = '1';
    }
  }

  // Draft persistence in sessionStorage so form entries survive rack navigation
  const DRAFT_KEY = 'addItemDraft_v1';
  function saveDraft() {
    try {
      const draft = {
        name: nameInput.value || '',
        selectedTags: selectedTags || [],
        otherNames: otherNamesInput.value || '',
        selectedColor: selectedColor || null,
        selectedSlots: selectedSlots || [],
        itemWidth: itemWidth || 1,
        rackId: currentRackId || null,
        ts: Date.now()
      };
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    } catch (e) {
      console.warn('Could not save draft', e);
    }
  }

  function loadDraft() {
    try {
      const raw = sessionStorage.getItem(DRAFT_KEY);
      if (!raw) return false;
      const d = JSON.parse(raw);
      // restore form values
      if (d.name) nameInput.value = d.name;
      selectedTags = Array.isArray(d.selectedTags) ? d.selectedTags.slice() : [];
      renderSelectedTags();
      if (d.otherNames) otherNamesInput.value = d.otherNames;
      if (d.selectedColor) {
        const sw = swatches.find(s => s.dataset.color === d.selectedColor);
        if (sw) selectSwatch(sw); else selectedColor = d.selectedColor;
      }
      if (d.itemWidth && widthInput) {
        widthInput.value = d.itemWidth;
        itemWidth = d.itemWidth;
      }
      // restore selected slots only if those slot IDs exist on this page
      selectedSlots = Array.isArray(d.selectedSlots) ? d.selectedSlots.filter(id => slots.some(s => s.dataset.slotId === id)) : [];
      // Do NOT toggle slot DOM selection here. We restore the draft silently so
      // the Add form does not automatically open when changing racks. The user
      // must click Add to enter add mode and see selections.
      return true;
    } catch (e) {
      console.warn('Could not load draft', e);
      return false;
    }
  }

  function clearDraft() {
    try { sessionStorage.removeItem(DRAFT_KEY); } catch(e){}
  }

  function renderSelectedTags() {
    selectedTagsContainer.innerHTML = '';
    selectedTags.forEach(tag => {
      const chip = document.createElement('span');
      chip.className = 'tag-chip';
      chip.textContent = tag;
      const rm = document.createElement('button');
      rm.className = 'tag-remove';
      rm.textContent = '×';
      rm.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedTags = selectedTags.filter(t => t !== tag);
        renderSelectedTags();
      });
      chip.appendChild(rm);
      selectedTagsContainer.appendChild(chip);
    });
  }

  function toggleTag(tag) {
    if (!tag) return;
    if (selectedTags.includes(tag)) {
      selectedTags = selectedTags.filter(t => t !== tag);
    } else {
      selectedTags.push(tag);
    }
    renderSelectedTags();
  }

  function selectSwatch(el) {
    swatches.forEach(s => s.classList.remove('selected'));
    if (!el) return;
    el.classList.add('selected');
    selectedColor = el.dataset.color || null;
  }

  // Wire preset tag buttons
  presetBtns.forEach(b => {
    b.addEventListener('click', () => {
      toggleTag(b.dataset.tag);
      saveDraft();
    });
  });

  // Custom tag add
  addCustomBtn.addEventListener('click', () => {
    const v = (customInput.value || '').trim();
    if (!v) return;
    if (!selectedTags.includes(v)) selectedTags.push(v);
    customInput.value = '';
    renderSelectedTags();
    saveDraft();
  });
  customInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addCustomBtn.click();
    }
  });

  // Color swatches
  swatches.forEach(s => s.addEventListener('click', () => selectSwatch(s)));

  // ensure swatch selection persists
  swatches.forEach(s => s.addEventListener('click', () => saveDraft()));

  // Slot click behavior
  slots.forEach(slot => {
    slot.addEventListener('click', (e) => {
      // If in add mode, toggle selection (but prevent selecting occupied)
      if (addMode) {
        if (slot.classList.contains('occupied')) return;
        slot.classList.toggle('selected');
        const id = slot.dataset.slotId;
        if (!id) return;
        if (slot.classList.contains('selected')) {
          if (!selectedSlots.includes(id)) selectedSlots.push(id);
        } else {
          selectedSlots = selectedSlots.filter(sid => sid !== id);
        }
        // persist selection
        saveDraft();
        return;
      }

      // Not add mode: if the slot is occupied, populate header and details
      if (!slot.classList.contains('occupied')) return;

      // Populate header fields (in templates/base.html)
      const headerName = document.getElementById('item-name-value');
      const headerLocation = document.getElementById('location-value');
      const headerTags = document.getElementById('tags-value');
      const headerOther = document.getElementById('other-names-value');
      if (headerName) headerName.textContent = slot.dataset.label || 'Unnamed Item';
      if (headerLocation) headerLocation.textContent = slot.dataset.location || slot.dataset.slotId || 'N/A';
      if (headerTags) {
        headerTags.innerHTML = '';
        const hdrTags = (slot.dataset.tags || '').split(',').map(s => s.trim()).filter(Boolean);
        if (hdrTags.length === 0) {
          headerTags.textContent = 'None';
        } else {
          hdrTags.forEach(t => {
            const chip = document.createElement('span');
            chip.className = 'tag-chip';
            chip.textContent = t;
            headerTags.appendChild(chip);
          });
        }
      }
      if (headerOther) headerOther.textContent = slot.dataset.otherNames || 'None';

      // Also populate detail panel if present
      const detailPanel = document.getElementById('item-details');
      if (detailPanel) {
        const detailName = document.getElementById('detail-name');
        const detailLocation = document.getElementById('detail-location');
        const detailTags = document.getElementById('detail-tags');
        const detailOther = document.getElementById('detail-other-names');

        if (detailName) detailName.textContent = slot.dataset.label || 'Unnamed Item';
        if (detailLocation) detailLocation.textContent = slot.dataset.location || slot.dataset.slotId || 'N/A';
        if (detailTags) {
          // render tag chips
          detailTags.innerHTML = '';
          const tags = (slot.dataset.tags || '').split(',').map(s => s.trim()).filter(Boolean);
          if (tags.length === 0) detailTags.textContent = 'None';
          tags.forEach(t => {
            const chip = document.createElement('span');
            chip.className = 'tag-chip';
            chip.textContent = t;
            detailTags.appendChild(chip);
          });
        }
        if (detailOther) detailOther.textContent = slot.dataset.otherNames || 'None';
        detailPanel.style.display = 'block';
      }
    });
  });

  // Save item
  saveBtn.addEventListener('click', async () => {
    const label = (nameInput.value || '').trim();
    if (!label) {
      alert('Please enter an item name.');
      nameInput.focus();
      return;
    }
    if (selectedSlots.length === 0) {
      alert('Please select at least one location on the rack.');
      return;
    }
    const otherRaw = (otherNamesInput.value || '').trim();
    const otherArr = otherRaw ? otherRaw.split(',').map(s => s.trim()).filter(Boolean) : [];

    try {
      const res = await fetch('/place', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slot_ids: selectedSlots,
          rack_id: currentRackId,
          label: label,
          tags: selectedTags,
          other_names: otherArr,
          color: selectedColor,
          width: itemWidth || 1
        })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.error || 'Failed to place item');
        return;
      }
      await res.json();
      // clear draft then refresh to show changes
      clearDraft();
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert('Network error. Please try again.');
    }
  });

  // Cancel add
  cancelBtn.addEventListener('click', () => { clearDraft(); setAddMode(false); });

  // Add button toggles add mode
  addBtn.addEventListener('click', () => { setAddMode(true); saveDraft(); });

  // Delete buttons (for occupied slots in edit mode)
  document.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const slot = btn.closest('.slot');
      const itemId = slot.dataset.itemId;
      const slotId = slot.dataset.slotId;
      if (!itemId) return;
      fetch('/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId, slot_id: slotId })
      }).then(() => window.location.reload());
    });
  });

  // Rack buttons preserve edit param and load rack's saved config
  const rackBtns = document.querySelectorAll('.rack-btn');
  console.log(`[Rack Buttons Found] Count: ${rackBtns.length}`);
  rackBtns.forEach(b => b.addEventListener('click', () => {
    const rackId = b.dataset.rack;
    // save draft so entries persist when navigating to another rack
    saveDraft();
    const params = new URLSearchParams(window.location.search);
    params.set('rack', rackId);
    // Load this rack's saved config from localStorage, or fall back to current
    const savedRackConfig = getSavedConfig(rackId);
    const configToUse = savedRackConfig || currentConfig
    // preserve edit
    const qs = params.toString();
    window.location = `/?${qs}`;
  }));

  // Edit mode button
  const editBtn = document.getElementById('edit-mode-btn');
  if (editBtn) {
    editBtn.addEventListener('click', () => {
      const params = new URLSearchParams(window.location.search);
      if (params.get('edit') === '1') params.delete('edit'); else params.set('edit', '1');
      const qs = params.toString();
      window.location = qs ? `/?${qs}` : '/';
    });
    if (window.location.search.includes('edit=1')) editBtn.textContent = 'Exit Edit Mode'; else editBtn.textContent = 'Edit Mode';
  }

  // Highlight current rack button
  const initial = currentRackId || '1';
  const sel = document.querySelector(`.rack-btn[data-rack="${initial}"]`);
  if (sel) {
    document.querySelectorAll('.rack-btn').forEach(b => b.classList.remove('active'));
    sel.classList.add('active');
  }

  // Width adjustment controls
  if (widthIncrease) {
    widthIncrease.addEventListener('click', () => {
      const maxCols = currentConfig === '4x4' ? 4 : 6;
      const currentVal = parseInt(widthInput.value) || 1;
      if (currentVal < maxCols) {
        widthInput.value = currentVal + 1;
        itemWidth = currentVal + 1;
        saveDraft();
      }
    });
  }

  if (widthDecrease) {
    widthDecrease.addEventListener('click', () => {
      const currentVal = parseInt(widthInput.value) || 1;
      if (currentVal > 1) {
        widthInput.value = currentVal - 1;
        itemWidth = currentVal - 1;
        saveDraft();
      }
    });
  }

  if (widthInput) {
    widthInput.addEventListener('change', () => {
      const maxCols = currentConfig === '4x4' ? 4 : 6;
      let val = parseInt(widthInput.value) || 1;
      if (val < 1) val = 1;
      if (val > maxCols) val = maxCols;
      widthInput.value = val;
      itemWidth = val;
      saveDraft();
    });
  }

  // Rack configuration buttons
  const configBtns = document.querySelectorAll('.config-btn');
  console.log(`[Config Buttons Found] Count: ${configBtns.length}`);
  configBtns.forEach(b => b.addEventListener('click', () => {
    const config = b.dataset.config;
    cfigBtns.forEach(b => b.addEventListener('click', () => {
    const config = b.dataset.config;
    // Save config to localStorage for this rack so it persists
    setSavedConfig(currentRackId, config);
    currentConfig = config;
    saveDraft();
    const params = new URLSearchParams(window.location.search);
    params.set('config', config);
    const qs = params.toString(
    }, 50);
  }));

  // Highlight current config button
  const currentConfigBtn = document.querySelector(`.config-btn[data-config="${currentConfig}"]`);
  if (currentConfigBtn) {
    document.querySelectorAll('.config-btn').forEach(b => b.classList.remove('active'));
    currentConfigBtn.classList.add('active');
  }

  // Attempt to restore draft if present
  loadDraft();
});
