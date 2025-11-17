-- models.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS racks (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  rows INTEGER NOT NULL,
  cols INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY,
  label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rack_slots (
  id INTEGER PRIMARY KEY,
  rack_id INTEGER NOT NULL,
  row INTEGER NOT NULL,
  col INTEGER NOT NULL,
  UNIQUE(rack_id, row, col),
  FOREIGN KEY(rack_id) REFERENCES racks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS item_slots (
  item_id INTEGER NOT NULL,
  slot_id INTEGER NOT NULL,
  item_label TEXT,
  rack_id INTEGER,
  PRIMARY KEY(item_id, slot_id),
  UNIQUE(slot_id),
  FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE,
  FOREIGN KEY(slot_id) REFERENCES rack_slots(id) ON DELETE CASCADE,
  FOREIGN KEY(rack_id) REFERENCES racks(id) ON DELETE CASCADE
);


