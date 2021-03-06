# manufacturing.py
#
# Copyright (C) 2016 - reuben
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

from gi.repository import Gtk, GLib
import subprocess
import barcode_generator
import main

UI_FILE = main.ui_directory + "/manufacturing.ui"


class Item(object):#this is used by py3o library see their example for more info
	pass


class ManufacturingGUI:
	def __init__(self, main):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(UI_FILE)
		self.builder.connect_signals(self)

		self.product_store = self.builder.get_object('product_store')
		product_completion = self.builder.get_object('product_completion')
		product_completion.set_match_func(self.product_match_func)

		self.product_id = None

		self.main = main
		self.db = main.db
		self.cursor = self.db.cursor()
		
		self.populate_stores ()
		
		self.window = self.builder.get_object('window1')
		self.window.show_all()

	def history_clicked (self, button):
		from reports import manufacturing_history 
		manufacturing_history.ManufacturingHistoryGUI (self.main)

	def product_match_func(self, completion, key, iter_):
		split_search_text = key.split()
		for text in split_search_text:
			if text not in self.product_store[iter_][1].lower():
				return False# no match
		return True# it's a hit!

	def product_match_selected(self, completion, model, iter_):
		self.product_id = model[iter_][0]
		self.product_selected()

	def product_combo_changed(self, combo):
		product_id = combo.get_active_id()
		if product_id != None:
			self.product_id = product_id
			self.product_selected ()

	def reprint_serial_number_clicked (self, button):
		barcode = self.builder.get_object('spinbutton3').get_value_as_int()
		self.print_serial_number(barcode, 1)

	def print_serial_number_clicked (self, button):
		serial_start = self.builder.get_object('spinbutton2').get_value_as_int()
		serial_number_qty = self.builder.get_object('spinbutton1').get_value_as_int()
		label_qty = self.builder.get_object('spinbutton4').get_value_as_int()
		for i in range(serial_number_qty):
			barcode = serial_start + i
			self.builder.get_object('serial_adjustment').set_lower(barcode)
			self.builder.get_object('spinbutton2').set_value (barcode)
			while Gtk.events_pending():
				Gtk.main_iteration()
			self.print_serial_number(barcode, label_qty)
			self.cursor.execute("INSERT INTO serial_numbers "
								"(product_id, date_inserted, serial_number, "
								"manufacturing_id) "
								"VALUES (%s, CURRENT_DATE, %s, %s)", 
								(self.product_id, barcode, self.project_id))
		serial = serial_number_qty + serial_start + 1
		self.cursor.execute("UPDATE products SET serial_number = %s "
							"WHERE id = %s", (serial, self.product_id))
		self.db.commit()

	def print_serial_number (self, barcode, label_qty):
		label = Item()
		label.code128 = barcode_generator.makeCode128(str(barcode))
		label.barcode = barcode
		from py3o.template import Template
		label_file = "/tmp/manufacturing_serial_label.odt"
		t = Template(main.template_dir+"/manufacturing_serial_template.odt", label_file )
		data = dict(label = label)
		t.render(data) #the self.data holds all the info
		for i in range(label_qty):
			subprocess.call(["soffice", "--headless", "-p", label_file])

	def start_serial_number_value_changed (self, spinbutton):
		serial_number = spinbutton.get_value_as_int()
		qty = self.builder.get_object('spinbutton1').get_value_as_int()
		self.builder.get_object('label10').set_label(str(qty + serial_number))

	def qty_spinbutton_changed (self,spinbutton):
		qty = spinbutton.get_value_as_int()
		serial_number = self.builder.get_object('spinbutton2').get_value_as_int()
		self.cursor.execute("SELECT name FROM products "
							"WHERE id = %s", (self.product_id,))
		for row in self.cursor.fetchall():
			product_name = row[0]
		manufacturing_name_string = "Manufacturing : %s [%s]" %(product_name, qty)
		self.builder.get_object('entry1').set_text(manufacturing_name_string)
		self.builder.get_object('entry2').set_text(manufacturing_name_string)
		self.builder.get_object('label10').set_label(str(qty + serial_number))
		
	def product_selected (self):
		self.cursor.execute("SELECT name, serial_number, assembly_notes "
							"FROM products "
							"WHERE id = %s", (self.product_id,))
		for row in self.cursor.fetchall():
			product_name = row[0]
			serial_number = row[1]
			self.builder.get_object('notes_buffer').set_text(row[2])
		self.builder.get_object('spinbutton2').set_value(int(serial_number))
		self.builder.get_object('serial_adjustment').set_lower(int(serial_number))
		self.builder.get_object('label2').set_label(" units of '%s'" % product_name)
		self.builder.get_object('combobox-entry').set_text(product_name)
		self.cursor.execute("SELECT id, name, time_clock_projects_id, qty "
							"FROM manufacturing_projects "
							"WHERE (product_id, active) = (%s, True)", 
							(self.product_id,))
		for row in self.cursor.fetchall():
			self.project_id = row[0]
			manufacturing_name = row[1]
			time_clock_projects_id = row[2]
			project_qty = row[3]
			self.builder.get_object('spinbutton1').set_value(project_qty)
			self.builder.get_object('entry2').set_text(manufacturing_name)
			self.cursor.execute("SELECT name FROM time_clock_projects "
								"WHERE id = %s", (time_clock_projects_id,))
			for row in self.cursor.fetchall():
				project_name = row[0]
				self.builder.get_object('entry1').set_text(project_name)
				self.builder.get_object('checkbutton1').set_active(True)
				break
			else:
				self.builder.get_object('checkbutton1').set_active(False)
				qty = self.builder.get_object('spinbutton1').get_text()
				manufacturing_name_string = "Manufacturing : %s [%s]" %(product_name, qty)
			self.cursor.execute("SELECT COUNT(DISTINCT(employee_id)), "
								"SUM(stop_time - start_time)::text "
								"FROM time_clock_entries "
								"WHERE (project_id, running) = "
								"(%s, False) GROUP BY project_id", 
								(time_clock_projects_id,))
			for row in self.cursor.fetchall():
				employee_count = row[0]
				formatted_time = row[1].split('.')[0]
				time_label = self.builder.get_object('label3')
				time_string = ("%s employee(s) spent "
								"%s (hour:minute:second) "
								"on this manufacturing process")\
								% (employee_count, formatted_time)
				time_label.set_label(time_string)
			self.builder.get_object('button4').set_sensitive(True)
			self.builder.get_object('button1').set_sensitive(True)
			self.builder.get_object('button3').set_sensitive(False)
			break
		else:
			self.builder.get_object('button4').set_sensitive(False)
			self.builder.get_object('button1').set_sensitive(False)
			self.builder.get_object('button3').set_sensitive(True)
			self.builder.get_object('checkbutton1').set_active(True)
			self.builder.get_object('spinbutton1').set_value(0)
			manufacturing_name_string = "Manufacturing : %s [0]" % product_name
			self.builder.get_object('entry2').set_text(manufacturing_name_string)
			#print (manufacturing_name_string)
			self.builder.get_object('entry1').set_text(manufacturing_name_string)

	def new_clicked (self, button):
		qty = self.builder.get_object('spinbutton1').get_text()
		manufacturing_name = self.builder.get_object('entry2').get_text()
		project_name = self.builder.get_object('entry1').get_text()
		if self.builder.get_object('checkbutton1').get_active() == True:
			# this manufacturing project is time tracked
			self.cursor.execute("INSERT INTO time_clock_projects "
								"(name, start_date, active, permanent) "
								"VALUES (%s, CURRENT_DATE, True, False) "
								"RETURNING id", 
								(project_name, ))
			time_clock_projects_id = self.cursor.fetchone()[0]
			self.cursor.execute("INSERT INTO manufacturing_projects "
								"(product_id, name, qty, time_clock_projects_id, "
								"active) VALUES (%s, %s, %s, %s, True) "
								"RETURNING id", 
								(self.product_id, manufacturing_name, 
								qty, time_clock_projects_id))
		else:
			self.cursor.execute("INSERT INTO manufacturing_projects "
								"(product_id, name, qty, active) "
								"VALUES (%s, %s, %s, True) RETURNING id", 
								(self.product_id, manufacturing_name, qty))
		self.project_id = self.cursor.fetchone()[0]
		self.db.commit()
		self.product_selected ()

	def update_clicked (self, button):
		qty = self.builder.get_object('spinbutton1').get_text()
		manufacturing_name = self.builder.get_object('entry2').get_text()
		project_name = self.builder.get_object('entry1').get_text()
		time_clock_active = self.builder.get_object('checkbutton1').get_active()
		self.cursor.execute("UPDATE manufacturing_projects SET "
							"(name, qty) = (%s, %s) WHERE id = %s", 
							(manufacturing_name, qty, self.project_id))
		self.cursor.execute("UPDATE time_clock_projects "
							"SET (name, active, stop_date) = "
							"(%s, %s, CURRENT_TIMESTAMP) WHERE id = "
								"(SELECT time_clock_projects_id "
								"FROM manufacturing_projects WHERE id = %s) "
								"RETURNING id",
							(project_name, time_clock_active, self.project_id))
		for row in self.cursor.fetchall():
			break  # updated successfully
		else:
			if time_clock_active == True: # create new time clock project
				self.cursor.execute("WITH cte AS (INSERT INTO time_clock_projects "
										"(name, start_date, active, permanent) "
										"VALUES (%s, CURRENT_DATE, True, False) "
										"RETURNING *) "
									"UPDATE manufacturing_projects "
									"SET time_clock_projects_id = (SELECT id FROM cte) "
									"WHERE id = %s", 
									(project_name, self.project_id))
		self.db.commit()

	def post_as_completed_clicked(self, button):
		self.cursor.execute("SELECT id, time_clock_projects_id "
							"FROM manufacturing_projects WHERE (id, active) = "
							"(%s, True)", (self.project_id,))
		for row in self.cursor.fetchall():
			time_clock_projects_id = row[1]
			self.cursor.execute("UPDATE manufacturing_projects "
								"SET active = False WHERE id = %s",
								(self.project_id,))
			self.cursor.execute("UPDATE time_clock_projects "
								"SET (active, stop_date) = "
								"(False, CURRENT_DATE) "
								"WHERE id = %s",
								(time_clock_projects_id,))
		self.db.commit()
		self.product_selected()

	def destroy(self, window):
		self.cursor.close()

	def focus (self, widget , event): 
		self.populate_stores ()
		
	def populate_stores(self):
		self.product_store.clear()
		self.cursor.execute("SELECT id, name FROM products "
							"WHERE (manufactured, deleted) = "
							"(True, False) ORDER BY name")
		for row in self.cursor.fetchall():
			product_id = row[0]
			product_name = row[1]
			self.product_store.append([str(product_id), product_name])

	def project_name_entry_icon_released (self, entry, icon_position, event):
		project_name = entry.get_text()
		self.builder.get_object('entry2').set_text(project_name)

	def product_window(self, column):
		import products
		products.ProductsGUI(self.main)
		


		
