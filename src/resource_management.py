# resource_management.py
#
# Copyright (C) 2017 - reuben
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, GLib, Gdk
from datetime import datetime, date
from dateutils import DateTimeCalendar
import spell_check
import main

UI_FILE = main.ui_directory + "/resource_management.ui"

class ResourceManagementGUI:
	timeout_id = None
	def __init__(self, main, id_ = None):

		self.builder = Gtk.Builder()
		self.builder.add_from_file(UI_FILE)
		self.builder.connect_signals(self)

		main.connect("shutdown", self.main_shutdown)
		self.main = main
		self.db = main.db
		self.cursor = main.db.cursor()
		self.editing = False
		self.timer_timeout = None
		
		self.resource_store = self.builder.get_object('resource_store')
		self.contact_store = self.builder.get_object('contact_store')
		self.contact_completion = self.builder.get_object('contact_completion')
		self.contact_completion.set_match_func(self.contact_match_func)
		self.tag_store = self.builder.get_object('tag_store')
		
		textview = self.builder.get_object('textview1')
		spell_check.add_checker_to_widget (textview)

		self.dated_for_calendar = DateTimeCalendar()
		no_date_button = self.builder.get_object('button5')
		self.dated_for_calendar.pack_start(no_date_button)
		date_label = self.builder.get_object('treeviewcolumn5').get_widget()
		self.dated_for_calendar.set_relative_to(date_label)
		self.dated_for_calendar.connect('day-selected', self.dated_for_calendar_day_selected )
		
		self.older_than_calendar = DateTimeCalendar()
		self.older_than_calendar.connect('day-selected', self.older_than_date_selected )
		self.older_than_calendar.set_today()
		self.populate_stores()
		self.populate_resource_store ()

		if id_ != None:
			selection = self.builder.get_object('treeview-selection1')
			for row in self.resource_store:
				if row[0] == id_:
					selection.select_path(row.path)
			self.editing_buffer = True
			self.cursor.execute("SELECT notes FROM resources "
								"WHERE id = %s", (id_,))
			for row in self.cursor.fetchall():
				text = row[0]
				self.builder.get_object('textbuffer1').set_text(text)
				break
			else:
				self.builder.get_object('textbuffer1').set_text('')
		self.editing_buffer = False
		
		self.window = self.builder.get_object('window1')
		self.window.show_all()

	def main_shutdown (self, main):
		if self.timeout_id:
			self.save_notes()

	def focus_in_event (self, window, event):
		self.populate_stores ()

	def unfinished_only_toggled (self, togglebutton):
		self.populate_resource_store ()
	
	def row_limit_value_changed (self, spinbutton):
		self.populate_resource_store ()

	def resource_threaded_checkbutton_toggled (self, checkbutton):
		self.populate_resource_store ()

	def treeview_button_release_event (self, treeview, event):
		if event.button == 3:
			menu = self.builder.get_object('menu1')
			menu.popup(None, None, None, None, event.button, event.time)
			menu.show_all()

	def delete_activated (self, menuitem):
		selection = self.builder.get_object('treeview-selection1')
		model, path = selection.get_selected_rows()
		if path != []:
			row_id = model[path][0]
			try:
				self.cursor.execute("DELETE FROM resources "
									"WHERE id = %s", (row_id,))
				self.db.commit()
			except Exception as e:
				self.show_message (e)
				self.db.rollback()
			self.populate_resource_store()

	def block_number_activated (self, menuitem):
		selection = self.builder.get_object('treeview-selection1')
		model, path = selection.get_selected_rows()
		if path != []:
			phone_number = model[path][11]
			try:
				self.cursor.execute("INSERT INTO phone_blacklist "
							"(number, blocked_calls) VALUES (%s, 0)", 
							(phone_number,))
				self.db.commit()
			except Exception as e:
				self.show_message (e)
				self.db.rollback()

	def row_activated (self, treeview, path, treeview_column):
		if self.timeout_id:
			self.save_notes()
		self.editing_buffer = True
		row_id = self.resource_store[path][0]
		self.cursor.execute("SELECT notes FROM resources "
							"WHERE id = %s", (row_id,))
		for row in self.cursor.fetchall():
			text = row[0]
			self.builder.get_object('textbuffer1').set_text(text)
			break
		else:
			self.builder.get_object('textbuffer1').set_text('')
		self.editing_buffer = False

	def contact_match_func(self, completion, key, iter):
		split_search_text = key.split()
		for text in split_search_text:
			if text not in self.contact_store[iter][1].lower():
				return False # no match
		return True # it's a hit!

	def contact_match_selected(self, completion, model, iter_):
		contact_id = model[iter_][0]
		selection = self.builder.get_object('treeview-selection1')
		tree_model, path = selection.get_selected_rows()
		id_ = tree_model[path][0]
		self.cursor.execute("UPDATE resources "
							"SET contact_id = %s "
							"WHERE id = %s", (contact_id, id_))
		self.db.commit()
		self.editing = False
		self.populate_resource_store(id_)

	def contact_editing_started (self, renderer_combo, combobox, path):
		self.editing = True
		entry = combobox.get_child()
		entry.set_completion(self.contact_completion)

	def contact_changed (self, renderer_combo, path, tree_iter):
		contact_id = self.contact_store[tree_iter][0]
		id_ = self.resource_store[path][0]
		self.cursor.execute("UPDATE resources "
							"SET contact_id = %s "
							"WHERE id = %s", (contact_id, id_))
		self.db.commit()
		self.editing = False
		self.populate_resource_store(id_)

	def contact_edited (self, renderer_combo, path, text):
		self.editing = False

	def contact_editing_canceled (self, renderer):
		self.editing = False

	def populate_stores (self):
		self.contact_store.clear()
		self.cursor.execute("SELECT id::text, name, ext_name, phone FROM contacts "
							"WHERE deleted = False ORDER BY name")
		for row in self.cursor.fetchall():
			contact_id = row[0]
			contact_name = row[1]
			ext_name = row[2]
			contact_phone = row[3]
			self.contact_store.append([contact_id, contact_name, ext_name, contact_phone])
		self.tag_store.clear()
		self.cursor.execute("SELECT id, tag, red, green, blue, alpha "
							"FROM resource_tags "
							"ORDER BY tag")
		for row in self.cursor.fetchall():
			tag_id = row[0]
			tag_name = row[1]
			rgba = Gdk.RGBA(1, 1, 1, 1)
			rgba.red = row[2]
			rgba.green = row[3]
			rgba.blue = row[4]
			rgba.alpha = row[5]
			self.tag_store.append([str(tag_id), tag_name, rgba])
			for row in self.resource_store:
				if row[8] == tag_id:
					row[10] = rgba

	def new_entry_clicked (self, button):
		self.cursor.execute("INSERT INTO resources "
								"(tag_id) "
								"SELECT id FROM resource_tags "
									"WHERE finished = False LIMIT 1 "
								"RETURNING id")
		new_id = self.cursor.fetchone()[0]
		self.populate_resource_store(new_id, new = True)
		
	def subject_editing_started (self, renderer_entry, entry, path):
		self.editing = True
		
	def subject_edited (self, renderer_text, path, text):
		self.editing = False
		id_ = self.resource_store[path][0]
		self.cursor.execute("UPDATE resources "
							"SET subject = %s "
							"WHERE id = %s", (text, id_))
		self.db.commit()
		self.resource_store[path][1] = text

	def subject_editing_canceled (self, renderer):
		self.editing = False

	def dated_for_calendar_day_selected (self, calendar):
		date = calendar.get_date()
		selection = self.builder.get_object('treeview-selection1')
		model, path = selection.get_selected_rows()
		id_ = model[path][0]
		self.cursor.execute("UPDATE resources "
							"SET dated_for = %s "
							"WHERE id = %s", (date, id_))
		self.db.commit()
		self.populate_resource_store(id_)

	def dated_for_editing_started (self, widget, entry, text):
		selection = self.builder.get_object('treeview-selection1')
		model, path = selection.get_selected_rows()
		row_id = model[path][0]
		self.cursor.execute("SELECT dated_for FROM resources "
							"WHERE id = %s AND dated_for IS NOT NULL", (row_id,))
		for row in self.cursor.fetchall():
			self.dated_for_calendar.set_datetime(row[0])
			break
		else:
			self.dated_for_calendar.set_today()
		GLib.idle_add(self.dated_for_calendar.show)

	def tag_editing_started (self, renderer_combo, combobox, path):
		self.editing = True

	def tag_changed (self, renderer_combo, path, tree_iter):
		self.editing = False
		tag_id = self.tag_store[tree_iter][0]
		id_ = self.resource_store[path][0]
		self.cursor.execute("UPDATE resources "
							"SET tag_id = %s "
							"WHERE id = %s; "
							"UPDATE time_clock_projects AS tcp "
							"SET active = NOT rt.finished "
							"FROM resource_tags AS rt "
							"WHERE (rt.id, rt.finished) = (%s, True) "
							"AND tcp.resource_id = %s",
							(tag_id, id_, tag_id, id_))
		self.db.commit()
		self.populate_resource_store(id_)

	def tag_editing_canceled (self, renderer):
		self.editing = False

	def text_buffer_changed (self, text_buffer):
		if self.editing_buffer == True:
			return
		selection = self.builder.get_object('treeview-selection1')
		model, path = selection.get_selected_rows()
		if path == []:
			self.show_message("Please select a row")
			return
		self.row_id = model[path][0]
		start = text_buffer.get_start_iter()
		end = text_buffer.get_end_iter()
		self.notes = text_buffer.get_text(start,end,True)
		if self.timeout_id:
			GLib.source_remove(self.timeout_id)
		self.timeout_id = GLib.timeout_add_seconds(10, self.save_notes)

	def save_notes (self ):
		if self.timeout_id:
			GLib.source_remove(self.timeout_id)
		self.cursor.execute("UPDATE resources SET notes = %s "
							"WHERE id = %s", (self.notes, self.row_id))
		self.db.commit()
		self.timeout_id = None

	def populate_resource_store (self, id_ = None, new = False):
		self.resource_store.clear()
		row_limit = self.builder.get_object('spinbutton1').get_value()
		finished = self.builder.get_object('checkbutton3').get_active()
		self.cursor.execute("SELECT "
								"rm.id, "
								"subject, "
								"COALESCE(contact_id, 0), "
								"COALESCE(name, ''), "
								"COALESCE(ext_name, ''), "
								"to_char(timed_seconds, 'HH24:MI:SS')::text, "
								"dated_for, "
								"format_date(dated_for), "
								"rmt.id, "
								"tag, "
								"red, "
								"green, "
								"blue, "
								"alpha, "
								"phone_number, "
								"call_received_time, "
								"format_timestamp(call_received_time), "
								"to_do "
							"FROM resources AS rm "
							"LEFT JOIN resource_tags AS rmt "
							"ON rmt.id = rm.tag_id "
							"LEFT JOIN contacts "
							"ON rm.contact_id = contacts.id "
							"WHERE date_created <= %s "
							"AND finished != %s OR finished IS NULL "
							"AND diary != True ORDER BY rm.id "
							"LIMIT %s", (self.older_than_date, finished, 
							row_limit))
		for row in self.cursor.fetchall():
			rgba = Gdk.RGBA(1, 1, 1, 1)
			row_id = row[0]
			subject = row[1]
			contact_id = row[2]
			contact_name = row[3]
			ext_name = row[4]
			time_formatted = row[5]
			dated_for = row[6]
			date_formatted = row[7]
			tag_id = row[8]
			tag_name = row[9]
			if tag_id == None:
				tag_id = 0
				tag_name = ''
			else:
				rgba.red = row[10]
				rgba.green = row[11]
				rgba.blue = row[12]
				rgba.alpha = row[13]
			phone_number = row[14]
			call_received_time = row[15]
			c_r_time_formatted = row[16]
			to_do = row[17]
			iter_ = self.resource_store.append([row_id, subject, contact_id,
										contact_name, ext_name, 0, 
										time_formatted, date_formatted, tag_id, 
										tag_name, rgba, phone_number,
										call_received_time, 
										c_r_time_formatted, to_do])
			if row_id == id_:
				self.builder.get_object('treeview-selection1').select_iter(iter_)
		if new == True:
			treeview = self.builder.get_object('treeview1')
			c = treeview.get_column(0)
			path = self.resource_store.get_path(iter_)
			treeview.set_cursor(path, c, True)
		
	def time_clock_project_clicked (self, button):
		selection = self.builder.get_object('treeview-selection1')
		model, path = selection.get_selected_rows()
		if path == []:
			self.show_message("Please select a row")
			return
		resource_id = model[path][0]
		subject = model[path][1]
		self.builder.get_object('project_name_entry').set_text(subject)
		dialog = self.builder.get_object('time_clock_create_dialog')
		result = dialog.run()
		dialog.hide()
		if result != Gtk.ResponseType.ACCEPT:
			return
		subject  = self.builder.get_object('project_name_entry').get_text()
		try:
			self.cursor.execute("INSERT INTO time_clock_projects "
								"(name, start_date, active, permanent, "
								"resource_id) "
								"VALUES (%s, now(), True, False, %s)"
								"ON CONFLICT (resource_id) "
								"DO UPDATE SET name = %s "
								"WHERE time_clock_projects.resource_id = %s", 
								(subject, resource_id, subject, resource_id))
		except Exception as e:
			self.show_message (e)
			self.db.rollback ()
			return
		self.db.commit()
		if self.builder.get_object('time_clock_checkbutton').get_active() == True:
			if not self.time_clock:
				import time_clock
				self.time_clock = time_clock.TimeClockGUI(self.main)
			else:
				self.time_clock.present()

	def older_than_entry_icon_released (self, entry, icon, event):
		self.older_than_calendar.set_relative_to(entry)
		self.older_than_calendar.show()

	def older_than_date_selected (self, calendar):
		date_text = calendar.get_text ()
		self.builder.get_object('entry1').set_text(date_text)
		self.older_than_date = calendar.get_date()
		self.populate_resource_store ()

	def tags_clicked (self, button):
		import resource_management_tags
		resource_management_tags.ResourceManagementTagsGUI (self.db)

	def no_date_clicked (self, button):
		selection = self.builder.get_object('treeview-selection1')
		model, path = selection.get_selected_rows()
		if path == []:
			return
		id_ = model[path][0]
		self.cursor.execute("UPDATE resources "
							"SET dated_for = NULL "
							"WHERE id = %s", ( id_, ))
		self.db.commit()
		self.populate_resource_store(id_)
		self.dated_for_calendar.hide()

	def to_do_toggled (self, renderer, path):
		active = not self.resource_store[path][14]
		self.resource_store[path][14] = active
		id_ = self.resource_store[path][0]
		self.cursor.execute("UPDATE resources SET to_do = %s "
							"WHERE id = %s", (active, id_))
		self.db.commit()
		
	def show_message (self, message):
		dialog = Gtk.MessageDialog( self.window,
									0,
									Gtk.MessageType.ERROR,
									Gtk.ButtonsType.CLOSE,
									str(message))
		dialog.run()
		dialog.destroy()

	def treeview_key_release_event (self, treeview, event):
		keyname = Gdk.keyval_name(event.keyval)
		path, col = treeview.get_cursor()
		# only visible columns!!
		columns = [c for c in treeview.get_columns() if c.get_visible()]
		colnum = columns.index(col)
		if keyname=="Tab" or keyname=="Esc":
			if colnum + 1 < len(columns):
				next_column = columns[colnum + 1]
			else:
				tmodel = treeview.get_model()
				titer = tmodel.iter_next(tmodel.get_iter(path))
				if titer is None:
					titer = tmodel.get_iter_first()
					path = tmodel.get_path(titer)
					next_column = columns[0]
			if keyname == 'Tab':
				GLib.timeout_add(10, treeview.set_cursor, path, next_column, True)
			elif keyname == 'Escape':
				pass




