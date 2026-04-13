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
  const rackCols = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--rack-cols'), 10) || 20;
  const rowColCellMap = new Map();
  const itemSlotIdsMap = new Map();
  let editBaseSlotIds = [];
  let livePreviewTimer = null;
  let lastLivePreviewKey = '';
  let resizeState = null;
  let lastResizeEndAt = 0;
  let suppressNextClick = false;
  const ENABLE_UI_DEBUG = true;

  function sendUiDebug(eventName, payload = {}) {
    if (!ENABLE_UI_DEBUG) return;
    const body = {
      event: eventName,
      rack_id: currentRackId,
      ...payload
    };
    fetch('/api/ui-debug', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      keepalive: true
    }).catch(() => {});
  }

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

  function clearSlotSelection() {
    selectedSlots = [];
    slots.forEach(s => s.classList.remove('selected'));
  }

  function normalizeSlotIds(slotIds) {
    if (!Array.isArray(slotIds)) return [];
    const out = [];
    slotIds.forEach(id => {
      const n = parseInt(id, 10);
      // Keep DB slot IDs as-is (positive ints). Backend translates to BLE 1..80.
      if (Number.isFinite(n) && n >= 1) out.push(String(n));
    });
    return Array.from(new Set(out));
  }

  function renderSelectionBySlotIds(slotIds) {
    const selected = new Set(normalizeSlotIds(slotIds));
    slots.forEach(slot => {
      const geo = getSlotGeometry(slot);
      if (!geo) {
        slot.classList.remove('selected');
        return;
      }

      const renderedSlotIds = extractSlotIdsForSlot(slot, geo.startCol, geo.endCol)
        .map(v => String(v).trim())
        .filter(Boolean);
      const isSelected = renderedSlotIds.some(id => selected.has(id));
      slot.classList.toggle('selected', isSelected);
    });
  }

  function sendLivePreview(slotIds) {
    const normalized = normalizeSlotIds(slotIds);
    if (!normalized.length) return;

    const payload = {
      rack_id: parseInt(currentRackId, 10),
      slot_ids: normalized,
      source: 'rack_edit_ui'
    };

    fetch('/api/live-highlight', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true
    }).catch(() => {});
  }

  function clearLivePreview() {
    lastLivePreviewKey = '';
    if (livePreviewTimer) {
      clearTimeout(livePreviewTimer);
      livePreviewTimer = null;
    }

    return fetch('/api/live-highlight', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rack_id: parseInt(currentRackId, 10),
        clear: true,
        source: 'rack_edit_ui'
      }),
      keepalive: true
    }).catch(() => {});
  }

  function scheduleLivePreview(slotIds, immediate = false) {
    const normalized = normalizeSlotIds(slotIds);
    if (!normalized.length) return;
    const key = `${currentRackId}:${normalized.join(',')}`;
    if (key === lastLivePreviewKey) return;
    lastLivePreviewKey = key;

    if (livePreviewTimer) {
      clearTimeout(livePreviewTimer);
      livePreviewTimer = null;
    }

    if (immediate) {
      sendLivePreview(normalized);
      return;
    }

    livePreviewTimer = setTimeout(() => {
      livePreviewTimer = null;
      sendLivePreview(normalized);
    }, 70);
  }

  function setEditButtonState(active) {
    const editItemBtn = document.getElementById('edit-item-btn');
    if (!editItemBtn) return;
    if (active) {
      editItemBtn.textContent = 'Exit Edit Mode';
      editItemBtn.style.background = '#5bc0de';
      editItemBtn.style.color = 'white';
    } else {
      editItemBtn.textContent = 'Edit Items';
      editItemBtn.style.background = '';
      editItemBtn.style.color = '';
    }
  }

  function enterInlineEditMode() {
    const currentParams = new URLSearchParams(window.location.search);
    if (currentParams.get('edit') !== 'item') {
      currentParams.set('edit', 'item');
      const qs = currentParams.toString();
      const newUrl = qs ? `/rack/${currentRackId}?${qs}` : `/rack/${currentRackId}`;
      window.history.replaceState({}, '', newUrl);
    }
    setEditButtonState(true);
    setupResizeHandles();
  }

  function populateSlotHeaderAndDetails(slot) {
    if (!slot || !slot.classList.contains('occupied')) return;

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
  }

  function loadSlotIntoEditor(slot) {
    const itemId = slot.dataset.itemId;
    if (!itemId) return;

    addMode = false;
    clearSlotSelection();
    editBaseSlotIds = Array.from(itemSlotIdsMap.get(itemId) || []).map(String);
    renderSelectionBySlotIds(editBaseSlotIds);
    scheduleLivePreview(editBaseSlotIds, true);

    nameInput.value = slot.dataset.label || '';

    const tagsStr = slot.dataset.tags || '';
    selectedTags = tagsStr.split(',').map(s => s.trim()).filter(Boolean);
    renderSelectedTags();

    otherNamesInput.value = slot.dataset.otherNames || '';

    const itemColor = slot.dataset.color;
    const colorSwatch = swatches.find(sw => sw.dataset.color === itemColor);
    if (colorSwatch) selectSwatch(colorSwatch);
    else selectedColor = itemColor;

    form.style.display = 'block';
    saveBtn.textContent = 'Update Item';
    saveBtn.dataset.itemId = itemId;
    saveBtn.dataset.editMode = 'true';

    // Keep the top summary section in sync while editing.
    populateSlotHeaderAndDetails(slot);
  }

  function isItemEditMode() {
    const currentParams = new URLSearchParams(window.location.search);
    return currentParams.get('edit') === 'item';
  }

  function setupResizeHandles() {
    document.querySelectorAll('.resize-handle').forEach(h => h.remove());
    if (!isItemEditMode()) return;

    slots.forEach(slot => {
      if (!slot.classList.contains('occupied')) return;

      const leftHandle = document.createElement('button');
      leftHandle.type = 'button';
      leftHandle.className = 'resize-handle resize-handle-left';
      leftHandle.setAttribute('aria-label', 'Resize item left');
      leftHandle.textContent = '⋮';

      const rightHandle = document.createElement('button');
      rightHandle.type = 'button';
      rightHandle.className = 'resize-handle resize-handle-right';
      rightHandle.setAttribute('aria-label', 'Resize item right');
      rightHandle.textContent = '⋮';

      leftHandle.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        e.stopPropagation();
        startResize(slot, e, 'left', leftHandle);
      });

      rightHandle.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        e.stopPropagation();
        startResize(slot, e, 'right', rightHandle);
      });

      slot.appendChild(leftHandle);
      slot.appendChild(rightHandle);
    });
  }

  function getRowFromContainer(slot) {
    const top = slot.closest('.rack-top');
    if (top) return 1;

    const rowEl = slot.closest('.rack-row');
    if (!rowEl) return null;
    const allRows = Array.from(document.querySelectorAll('.rack-bottom .rack-row'));
    const idx = allRows.indexOf(rowEl);
    if (idx === -1) return null;
    return idx + 2;
  }

  function getSlotSpan(slot) {
    const style = slot.getAttribute('style') || '';
    const m = style.match(/grid-column\s*:\s*span\s*(\d+)/i);
    if (m) {
      const n = parseInt(m[1], 10);
      if (Number.isFinite(n) && n > 0) return n;
    }
    const dataStart = parseInt(slot.dataset.colStart || '', 10);
    const dataEnd = parseInt(slot.dataset.colEnd || '', 10);
    if (Number.isFinite(dataStart) && Number.isFinite(dataEnd) && dataEnd >= dataStart) {
      return (dataEnd - dataStart) + 1;
    }
    return 1;
  }

  function getSlotGeometry(slot) {
    const row = parseInt(slot.dataset.row || '', 10) || getRowFromContainer(slot);
    if (!Number.isFinite(row)) return null;

    const dataStart = parseInt(slot.dataset.colStart || '', 10);
    const dataEnd = parseInt(slot.dataset.colEnd || '', 10);
    if (Number.isFinite(dataStart) && Number.isFinite(dataEnd) && dataEnd >= dataStart) {
      return { row, startCol: dataStart, endCol: dataEnd };
    }

    const rowContainer = slot.closest('.rack-row') || slot.closest('.rack-top');
    if (!rowContainer) return null;

    let colCursor = 1;
    const rowSlots = Array.from(rowContainer.querySelectorAll('.slot'));
    for (const s of rowSlots) {
      const span = getSlotSpan(s);
      const startCol = colCursor;
      const endCol = colCursor + span - 1;
      if (s === slot) return { row, startCol, endCol };
      colCursor = endCol + 1;
    }

    return null;
  }

  function extractSlotIdsForSlot(slot, startCol, endCol) {
    const fromData = (slot.dataset.slotIds || '')
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);
    if (fromData.length) return fromData;

    const fromLocation = (slot.dataset.location || '')
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);
    if (fromLocation.length) return fromLocation;

    const single = (slot.dataset.slotId || '').trim();
    if (single) {
      const spanLen = Math.max(1, (endCol - startCol) + 1);
      return [single, ...Array.from({ length: spanLen - 1 }, () => '')];
    }

    return [];
  }

  function normalizeItemId(rawItemId) {
    const value = String(rawItemId || '').trim();
    if (!value) return '';
    if (/^(none|null|undefined)$/i.test(value)) return '';
    return value;
  }

  function buildCellMaps() {
    rowColCellMap.clear();
    itemSlotIdsMap.clear();

    slots.forEach(slot => {
      const geo = getSlotGeometry(slot);
      if (!geo) return;
      const row = geo.row;
      const colStart = geo.startCol;
      const colEnd = geo.endCol;

      const itemId = normalizeItemId(slot.dataset.itemId);
      const parsedSlotIds = extractSlotIdsForSlot(slot, colStart, colEnd);

      let index = 0;
      for (let c = colStart; c <= colEnd; c += 1) {
        const fallbackSlotId = c === colStart ? (slot.dataset.slotId || '').trim() : '';
        const slotId = parsedSlotIds[index] || fallbackSlotId;
        rowColCellMap.set(`${row}:${c}`, { itemId, slotId: slotId || '' });

        if (itemId && slotId) {
          if (!itemSlotIdsMap.has(itemId)) itemSlotIdsMap.set(itemId, new Set());
          itemSlotIdsMap.get(itemId).add(slotId);
        }
        index += 1;
      }
    });
  }

  function getRangeSlotIds(row, colStart, colEnd) {
    const ids = [];
    for (let c = colStart; c <= colEnd; c += 1) {
      const cell = rowColCellMap.get(`${row}:${c}`);
      if (cell && cell.slotId) ids.push(cell.slotId);
    }
    return ids;
  }

  function getAllowedLeft(itemId, row, rightCol) {
    let allowedLeft = 1;
    for (let c = rightCol; c >= 1; c -= 1) {
      const cell = rowColCellMap.get(`${row}:${c}`);
      if (cell && cell.itemId && cell.itemId !== itemId) {
        allowedLeft = c + 1;
        break;
      }
      allowedLeft = c;
    }
    return allowedLeft;
  }

  function getAllowedRight(itemId, row, leftCol) {
    let allowedRight = rackCols;
    for (let c = leftCol; c <= rackCols; c += 1) {
      const cell = rowColCellMap.get(`${row}:${c}`);
      if (cell && cell.itemId && cell.itemId !== itemId) {
        allowedRight = c - 1;
        break;
      }
      allowedRight = c;
    }
    return allowedRight;
  }

  function getPointerColumn(rowContainer, clientX) {
    const rect = rowContainer.getBoundingClientRect();
    if (rect.width <= 0) return 1;
    const unitWidth = rect.width / rackCols;
    const offsetX = Math.max(0, Math.min(rect.width - 1, clientX - rect.left));
    const col = Math.floor(offsetX / unitWidth) + 1;
    return Math.max(1, Math.min(rackCols, col));
  }

  function getHoveredColumnForResize(e, state) {
    const el = document.elementFromPoint(e.clientX, e.clientY);
    if (!el) return null;
    const hoveredSlot = el.closest('.slot');
    if (!hoveredSlot) return null;

    if ((hoveredSlot.dataset.itemId || '').trim() === state.itemId) return null;

    const geo = getSlotGeometry(hoveredSlot);
    if (!geo || geo.row !== state.row) return null;

    if (state.direction === 'left') return geo.startCol;
    if (state.direction === 'right') return geo.endCol;
    return geo.startCol;
  }

  function previewResizeRange(row, leftCol, rightCol) {
    clearSlotSelection();
    selectedSlots = getRangeSlotIds(row, leftCol, rightCol);

    slots.forEach(s => {
      const geo = getSlotGeometry(s);
      if (!geo) return;
      const sRow = geo.row;
      const sStart = geo.startCol;
      const sEnd = geo.endCol;
      if (sRow !== row) return;
      const overlaps = !(sEnd < leftCol || sStart > rightCol);
      if (overlaps) s.classList.add('selected');
    });
  }

  function buildResizePreviewSlotIds(state, currentIds) {
    const allIdsSet = new Set(Array.from(itemSlotIdsMap.get(state.itemId) || []).map(String));
    state.baseIds.forEach(id => allIdsSet.delete(String(id)));
    currentIds.forEach(id => allIdsSet.add(String(id)));
    return Array.from(allIdsSet).filter(Boolean);
  }

  async function persistResizedSlots(itemId, resizeInfo, slotIds) {
    sendUiDebug('persist_begin', {
      item_id: itemId,
      row: resizeInfo.row,
      left: resizeInfo.leftCol,
      right: resizeInfo.rightCol
    });

    const label = (nameInput.value || '').trim();
    const otherRaw = (otherNamesInput.value || '').trim();
    const otherArr = otherRaw ? otherRaw.split(',').map(s => s.trim()).filter(Boolean) : [];

    const res = await fetch(`/items/${itemId}/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        label: label || 'Unnamed Item',
        tags: selectedTags,
        other_names: otherArr,
        color: selectedColor,
        resize_row: resizeInfo.row,
        resize_col_start: resizeInfo.leftCol,
        resize_col_end: resizeInfo.rightCol,
        slot_ids: slotIds,
        rack_id: currentRackId
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      sendUiDebug('persist_error', {
        item_id: itemId,
        reason: err.error || 'http_not_ok'
      });
      throw new Error(err.error || 'Failed to resize item');
    }

    sendUiDebug('persist_ok', { item_id: itemId });
  }

  function handleResizeMove(e) {
    if (!resizeState) return;
    if (e.pointerId !== undefined && resizeState.pointerId !== undefined && e.pointerId !== resizeState.pointerId) return;

    const next = computeResizeCurrent(resizeState, e.clientX);

    if (!resizeState.debugMoveSent) {
      resizeState.debugMoveSent = true;
      sendUiDebug('drag_move', {
        item_id: resizeState.itemId,
        row: resizeState.row,
        left: resizeState.baseLeftCol,
        right: resizeState.baseRightCol
      });
    }

    if (!next) return;
    resizeState.current = next;
    previewResizeRange(resizeState.row, next.leftCol, next.rightCol);
    const previewIds = buildResizePreviewSlotIds(resizeState, next.ids.map(String));
    scheduleLivePreview(previewIds, false);
  }

  function handleResizeMouseMove(e) {
    if (!resizeState) return;
    handleResizeMove({
      clientX: e.clientX,
      pointerId: resizeState.pointerId
    });
  }

  function handleResizeMouseUp(e) {
    if (!resizeState) return;
    handleResizeUp({
      clientX: e.clientX,
      pointerId: resizeState.pointerId
    });
  }

  function computeResizeCurrent(state, clientX) {
    const pointerCol = getPointerColumn(state.rowContainer, clientX);
    const startPointerCol = Number.isFinite(state.startPointerCol)
      ? state.startPointerCol
      : pointerCol;
    const deltaCols = pointerCol - startPointerCol;

    if (state.direction === 'left') {
      const minLeft = 1;
      const maxLeft = state.endCol;
      const byDelta = state.baseLeftCol + deltaCols;
      const desiredLeft = Math.min(byDelta, pointerCol);
      const leftCol = Math.max(minLeft, Math.min(desiredLeft, maxLeft));
      const ids = getRangeSlotIds(state.row, leftCol, state.endCol);
      const resolvedIds = ids.length ? ids : state.baseIds;
      if (!resolvedIds.length) return null;
      return { leftCol, rightCol: state.endCol, ids: resolvedIds };
    }

    const maxRight = rackCols;
    const minRight = state.startCol;
    const byDelta = state.baseRightCol + deltaCols;
    const desiredRight = Math.max(byDelta, pointerCol);
    const rightCol = Math.min(maxRight, Math.max(desiredRight, minRight));
    const ids = getRangeSlotIds(state.row, state.startCol, rightCol);
    const resolvedIds = ids.length ? ids : state.baseIds;
    if (!resolvedIds.length) return null;
    return { leftCol: state.startCol, rightCol, ids: resolvedIds };
  }

  async function handleResizeUp() {
    if (resizeState && arguments.length > 0) {
      const e = arguments[0];
      if (e && e.pointerId !== undefined && resizeState.pointerId !== undefined && e.pointerId !== resizeState.pointerId) {
        return;
      }
    }

    window.removeEventListener('pointermove', handleResizeMove);
    window.removeEventListener('pointerup', handleResizeUp);
    window.removeEventListener('pointercancel', handleResizeUp);
    window.removeEventListener('mousemove', handleResizeMouseMove);
    window.removeEventListener('mouseup', handleResizeMouseUp);
    document.removeEventListener('pointermove', handleResizeMove, true);
    document.removeEventListener('pointerup', handleResizeUp, true);
    document.removeEventListener('pointercancel', handleResizeUp, true);
    document.removeEventListener('mousemove', handleResizeMouseMove, true);
    document.removeEventListener('mouseup', handleResizeMouseUp, true);
    document.body.style.userSelect = '';
    document.body.style.cursor = '';
    if (!resizeState) return;

    const state = resizeState;
    resizeState = null;
    lastResizeEndAt = Date.now();

    if (arguments.length > 0) {
      const e = arguments[0];
      if (e && Number.isFinite(e.clientX)) {
        const endCurrent = computeResizeCurrent(state, e.clientX);
        if (endCurrent) state.current = endCurrent;
      }
    }

    if (!state.current) {
      sendUiDebug('drag_end_no_change', {
        item_id: state.itemId,
        reason: 'no_current'
      });
      return;
    }

    suppressNextClick = true;

    const currentIds = state.current.ids.map(String);
    const sameSize =
      state.current.leftCol === state.baseLeftCol
      && state.current.rightCol === state.baseRightCol;
    if (sameSize) {
      sendUiDebug('drag_end_same_size', {
        item_id: state.itemId,
        row: state.row,
        left: state.baseLeftCol,
        right: state.baseRightCol,
        reason: 'no_column_change_or_blocked'
      });
      state.activeSlot.style.transition = '';
      const originalPreview = buildResizePreviewSlotIds(state, state.baseIds.map(String));
      scheduleLivePreview(originalPreview, true);
      return;
    }

    const allIdsSet = new Set(Array.from(itemSlotIdsMap.get(state.itemId) || []).map(String));
    state.baseIds.forEach(id => allIdsSet.delete(String(id)));
    currentIds.forEach(id => allIdsSet.add(String(id)));
    const finalIds = Array.from(allIdsSet).filter(Boolean);

    if (!finalIds.length) {
      sendUiDebug('drag_end_invalid', {
        item_id: state.itemId,
        reason: 'empty_final_ids'
      });
      alert('Item must occupy at least one slot.');
      return;
    }

    try {
      await persistResizedSlots(
        state.itemId,
        { row: state.row, leftCol: state.current.leftCol, rightCol: state.current.rightCol },
        finalIds
      );
      scheduleLivePreview(finalIds, true);
      clearDraft();
      window.location.reload();
    } catch (err) {
      console.error(err);
      state.activeSlot.style.transition = '';
      alert(err.message || 'Could not resize item.');
    }
  }

  function startResize(slot, e, forcedDirection = null, handleEl = null) {
    if (typeof e.button === 'number' && e.button !== 0) return;
    if (e.pointerType && e.isPrimary === false) return;
    if (resizeState) return;
    if ((Date.now() - lastResizeEndAt) < 120) return;

    const params = new URLSearchParams(window.location.search);
    const editMode = params.get('edit');
    if (editMode !== 'item' || addMode || !slot.classList.contains('occupied')) {
      sendUiDebug('drag_blocked', {
        reason: `editMode=${editMode}|addMode=${addMode}|occupied=${slot.classList.contains('occupied')}`
      });
      return;
    }

    const geo = getSlotGeometry(slot);
    if (!geo) {
      sendUiDebug('drag_blocked', { reason: 'no_geometry' });
      return;
    }
    const row = geo.row;
    const startCol = geo.startCol;
    const endCol = geo.endCol;
    const itemId = (slot.dataset.itemId || '').trim();
    if (!Number.isFinite(row) || !Number.isFinite(startCol) || !Number.isFinite(endCol) || !itemId) {
      sendUiDebug('drag_blocked', { reason: 'invalid_geometry_or_item' });
      return;
    }

    const rowContainer = slot.closest('.rack-row') || slot.closest('.rack-top');
    if (!rowContainer) {
      sendUiDebug('drag_blocked', { reason: 'no_row_container' });
      return;
    }

    // Do not rebuild handles here; removing the active handle can cancel drag start.
    loadSlotIntoEditor(slot);

    resizeState = {
      activeSlot: slot,
      itemId,
      row,
      startCol,
      endCol,
      rowContainer,
      startX: e.clientX,
      colWidth: Math.max(1, rowContainer.getBoundingClientRect().width / rackCols),
      startPointerCol: getPointerColumn(rowContainer, e.clientX),
      pointerId: e.pointerId,
      originalGridColumn: slot.style.gridColumn || '',
      direction: forcedDirection,
      forcedDirection,
      debugMoveSent: false,
      baseLeftCol: startCol,
      baseRightCol: endCol,
      baseIds: getRangeSlotIds(row, startCol, endCol),
      current: {
        leftCol: startCol,
        rightCol: endCol,
        ids: getRangeSlotIds(row, startCol, endCol)
      }
    };

    resizeState.activeSlot.style.transition = 'none';

    sendUiDebug('drag_start', {
      item_id: itemId,
      row,
      left: startCol,
      right: endCol
    });

    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'ew-resize';
    if (handleEl && typeof handleEl.setPointerCapture === 'function' && e.pointerId !== undefined) {
      try {
        handleEl.setPointerCapture(e.pointerId);
      } catch (_err) {
        // Ignore pointer capture failures on unsupported browsers/devices.
      }
    }
    window.addEventListener('pointermove', handleResizeMove);
    window.addEventListener('pointerup', handleResizeUp);
    window.addEventListener('pointercancel', handleResizeUp);
    window.addEventListener('mousemove', handleResizeMouseMove);
    window.addEventListener('mouseup', handleResizeMouseUp);
    document.addEventListener('pointermove', handleResizeMove, true);
    document.addEventListener('pointerup', handleResizeUp, true);
    document.addEventListener('pointercancel', handleResizeUp, true);
    document.addEventListener('mousemove', handleResizeMouseMove, true);
    document.addEventListener('mouseup', handleResizeMouseUp, true);
  }

  buildCellMaps();
  setupResizeHandles();

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
      if (suppressNextClick) {
        suppressNextClick = false;
        return;
      }

      // Check if we're in edit item mode
      const urlParams = new URLSearchParams(window.location.search);
      const editMode = urlParams.get('edit');
      
      // If in edit item mode
      if (editMode === 'item') {
        // If slot is occupied, load item for editing
        if (slot.classList.contains('occupied')) {
          loadSlotIntoEditor(slot);
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
            const liveSlots = normalizeSlotIds([...editBaseSlotIds, ...selectedSlots]);
            scheduleLivePreview(liveSlots, true);
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

      // Outside add mode, clicking an occupied slot should immediately enter item editing.
      if (slot.classList.contains('occupied') && editMode !== 'remove') {
        enterInlineEditMode();
        loadSlotIntoEditor(slot);
        return;
      }

      // Not add mode: if the slot is occupied, populate header and details
      if (!slot.classList.contains('occupied')) return;

      populateSlotHeaderAndDetails(slot);
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
      const params = new URLSearchParams(window.location.search);
      const isRemoveMode = params.get('edit') === 'remove';
      const payload = isRemoveMode
        ? { item_id: itemId }
        : { item_id: itemId, slot_id: slotId };
      fetch('/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
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
      const isExitingEditMode = params.get('edit') === 'item';
      if (isExitingEditMode) {
        clearLivePreview();
        params.delete('edit');
      } else {
        params.set('edit', 'item');
      }
      const qs = params.toString();
      window.location = qs ? `/rack/${currentRackId}?${qs}` : `/rack/${currentRackId}`;
    });
    setEditButtonState(window.location.search.includes('edit=item'));
  }

  const backToRacksLink = document.querySelector('a[href="/edit-racks"]');
  if (backToRacksLink) {
    backToRacksLink.addEventListener('click', async (event) => {
      event.preventDefault();
      try {
        await clearLivePreview();
      } finally {
        window.location = backToRacksLink.href;
      }
    });
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
