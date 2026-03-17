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

  // State
  let addMode = false;
  let selectedSlots = [];
  let selectedTags = [];
  let selectedColor = null;
  const params = new URLSearchParams(window.location.search);
  // Extract rack ID from URL path (e.g., /rack/1 -> 1)
  const pathParts = window.location.pathname.split('/');
  let currentRackId = pathParts[pathParts.length - 1] || '1';
  
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
      form.style.display = 'none';
    } else {
      form.style.display = 'block';
      nameInput.focus();
      // Scroll form into view smoothly
      setTimeout(() => {
        form.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 100);
      // default first swatch
      if (swatches.length) {
        selectSwatch(swatches[0]);
      }
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
      // Check if we're in edit item mode
      const urlParams = new URLSearchParams(window.location.search);
      const editMode = urlParams.get('edit');
      
      // If in edit item mode
      if (editMode === 'item') {
        // If slot is occupied, load item for editing
        if (slot.classList.contains('occupied')) {
          const itemId = slot.dataset.itemId;
          if (!itemId) return;
          
          // Populate form with item data
          nameInput.value = slot.dataset.label || '';
          
          // Parse and set tags
          const tagsStr = slot.dataset.tags || '';
          selectedTags = tagsStr.split(',').map(s => s.trim()).filter(Boolean);
          renderSelectedTags();
          
          // Set other names
          otherNamesInput.value = slot.dataset.otherNames || '';
          
          // Set color
          const itemColor = slot.dataset.color;
          const colorSwatch = swatches.find(sw => sw.dataset.color === itemColor);
          if (colorSwatch) selectSwatch(colorSwatch);
          else selectedColor = itemColor;
          
          // Show form
          form.style.display = 'block';
          
          // Change save button to update mode
          saveBtn.textContent = 'Update Item';
          saveBtn.dataset.itemId = itemId;
          saveBtn.dataset.editMode = 'true';
          
          return;
        } else {
          // If slot is empty and form is visible (item loaded for editing), allow selecting additional slots
          if (form.style.display === 'block' && saveBtn.dataset.editMode === 'true') {
            slot.classList.toggle('selected');
            const id = slot.dataset.slotId;
            if (!id) return;
            if (slot.classList.contains('selected')) {
              if (!selectedSlots.includes(id)) selectedSlots.push(id);
            } else {
              selectedSlots = selectedSlots.filter(sid => sid !== id);
            }
            saveDraft();
            return;
          }
        }
      }
      
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
      const headerTags = document.getElementById('tags-value');
      const headerOther = document.getElementById('other-names-value');
      if (headerName) headerName.textContent = slot.dataset.label || 'Unnamed Item';
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
    
    const isEditMode = saveBtn.dataset.editMode === 'true';
    const itemId = saveBtn.dataset.itemId;
    
    // For edit mode, slots are optional (can just update properties)
    // For add mode, at least one slot is required
    if (!isEditMode && selectedSlots.length === 0) {
      alert('Please select at least one location on the rack.');
      return;
    }
    
    const otherRaw = (otherNamesInput.value || '').trim();
    const otherArr = otherRaw ? otherRaw.split(',').map(s => s.trim()).filter(Boolean) : [];

    try {
      let res;
      
      if (isEditMode && itemId) {
        // Update existing item
        res = await fetch(`/items/${itemId}/update`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            label: label,
            tags: selectedTags,
            other_names: otherArr,
            color: selectedColor,
            additional_slots: selectedSlots,  // Add to more slots if selected
            rack_id: currentRackId
          })
        });
      } else {
        // Create and place new item
        res = await fetch('/place', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            slot_ids: selectedSlots,
            rack_id: currentRackId,
            label: label,
            tags: selectedTags,
            other_names: otherArr,
            color: selectedColor
          })
        });
      }
      
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.error || `Failed to ${isEditMode ? 'update' : 'place'} item`);
        return;
      }
      await res.json();
      // clear draft then refresh to show changes
      clearDraft();
      // Reset save button state
      saveBtn.textContent = 'Save Item';
      delete saveBtn.dataset.editMode;
      delete saveBtn.dataset.itemId;
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert('Network error. Please try again.');
    }
  });

  // Cancel add/edit
  cancelBtn.addEventListener('click', () => { 
    clearDraft(); 
    setAddMode(false);
    // Reset save button state
    saveBtn.textContent = 'Save Item';
    delete saveBtn.dataset.editMode;
    delete saveBtn.dataset.itemId;
    // Reset add button state
    addBtn.textContent = 'Add New Item';
    addBtn.style.background = '';
    addBtn.style.color = '';
  });

  // Add button toggles add mode
  addBtn.addEventListener('click', () => { 
    if (addMode) {
      setAddMode(false);
      addBtn.textContent = 'Add New Item';
      addBtn.style.background = '';
      addBtn.style.color = '';
    } else {
      setAddMode(true); 
      saveDraft();
      addBtn.textContent = 'Cancel Add';
      addBtn.style.background = '#5bc0de';
      addBtn.style.color = 'white';
    }
  });

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

  // Remove Items button (shows delete buttons on items)
  const removeItemsBtn = document.getElementById('remove-items-btn');
  if (removeItemsBtn) {
    removeItemsBtn.addEventListener('click', () => {
      const params = new URLSearchParams(window.location.search);
      if (params.get('edit') === 'remove') params.delete('edit'); else params.set('edit', 'remove');
      const qs = params.toString();
      window.location = qs ? `/rack/${currentRackId}?${qs}` : `/rack/${currentRackId}`;
    });
    if (window.location.search.includes('edit=remove')) {
      removeItemsBtn.textContent = 'Exit Remove Mode';
      removeItemsBtn.style.background = '#d9534f';
      removeItemsBtn.style.color = 'white';
    } else {
      removeItemsBtn.textContent = 'Remove Items';
      removeItemsBtn.style.background = '';
      removeItemsBtn.style.color = '';
    }
  }

  // Edit Item button (allows editing item properties)
  const editItemBtn = document.getElementById('edit-item-btn');
  if (editItemBtn) {
    editItemBtn.addEventListener('click', () => {
      const params = new URLSearchParams(window.location.search);
      if (params.get('edit') === 'item') params.delete('edit'); else params.set('edit', 'item');
      const qs = params.toString();
      window.location = qs ? `/rack/${currentRackId}?${qs}` : `/rack/${currentRackId}`;
    });
    if (window.location.search.includes('edit=item')) {
      editItemBtn.textContent = 'Exit Edit Mode';
      editItemBtn.style.background = '#5bc0de';
      editItemBtn.style.color = 'white';
    } else {
      editItemBtn.textContent = 'Edit Items';
      editItemBtn.style.background = '';
      editItemBtn.style.color = '';
    }
  }

  // Rack configuration buttons (only those with data-config attribute)
  const configBtns = document.querySelectorAll('.config-btn[data-config]');
  configBtns.forEach(b => b.addEventListener('click', async () => {
    const config = b.dataset.config;
    // Save config to localStorage for this rack so it persists
    setSavedConfig(currentRackId, config);
    currentConfig = config;
    saveDraft();
    
    // Save to database as well
    try {
      await fetch(`/rack/${currentRackId}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: config })
      });
    } catch (err) {
      console.error('Failed to save config to database:', err);
    }
    
    const params = new URLSearchParams(window.location.search);
    params.set('config', config);
    const qs = params.toString();
    // Add small delay to ensure localStorage write completes before reload
    setTimeout(() => {
      window.location = `/rack/${currentRackId}?${qs}`;
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
