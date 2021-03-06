# customer_history.py
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


from gi.repository import Gtk
from decimal import Decimal
import subprocess
import main

UI_FILE = main.ui_directory + "/reports/product_history.ui"

class ProductHistoryGUI:
	def __init__(self, main):

		self.search_iter = 0
		
		self.builder = Gtk.Builder()
		self.builder.add_from_file(UI_FILE)
		self.builder.connect_signals(self)

		product_completion = self.builder.get_object('product_completion')
		product_completion.set_match_func(self.product_match_func)

		self.main = main
		self.db = main.db
		self.cursor = self.db.cursor()

		self.invoice_history = None

		self.product_store = self.builder.get_object('product_store')
		self.cursor.execute("SELECT id::text, name, ext_name FROM products "
							"WHERE deleted = False ORDER BY name")
		for row in self.cursor.fetchall():
			id_ = row[0]
			name = row[1]
			ext_name = row[2]
			self.product_store.append([id_ , name, ext_name])
			
		qty_column = self.builder.get_object ('treeviewcolumn4')
		qty_renderer = self.builder.get_object ('cellrenderertext4')
		qty_column.set_cell_data_func(qty_renderer, self.qty_cell_func, 5)
			
		price_column = self.builder.get_object ('treeviewcolumn5')
		price_renderer = self.builder.get_object ('cellrenderertext5')
		price_column.set_cell_data_func(price_renderer, self.price_cell_func, 6)

		price_column = self.builder.get_object ('treeviewcolumn8')
		price_renderer = self.builder.get_object ('cellrenderertext9')
		price_column.set_cell_data_func(price_renderer, self.price_cell_func, 5)
		
		self.window = self.builder.get_object('window1')
		self.window.show_all()

	def close_transaction_window (self, window, event):
		self.cursor.close()

	def qty_cell_func(self, view_column, cellrenderer, model, iter1, column):
		price = '{:,.1f}'.format(model.get_value(iter1, column))
		cellrenderer.set_property("text" , price)

	def price_cell_func(self, view_column, cellrenderer, model, iter1, column):
		price = '{:,.2f}'.format(model.get_value(iter1, column))
		cellrenderer.set_property("text" , price)
		
	def invoice_row_activated (self, treeview, treepath, treeviewcolumn):
		model = treeview.get_model()
		file_id = model[treepath][0]
		self.cursor.execute("SELECT name, pdf_data FROM invoices WHERE id = %s", 
																	(file_id ,))
		for row in self.cursor.fetchall():
			file_name = "/tmp/" + row[0]
			if file_name == None:
				return
			file_data = row[1]
			f = open(file_name,'wb')
			f.write(file_data)
			subprocess.call(["xdg-open", file_name])
			f.close()

	def invoice_treeview_button_release_event (self, treeview, event):
		selection = self.builder.get_object('treeview-selection4')
		model, path = selection.get_selected_rows()
		if path == []:
			return
		if event.button == 3:
			menu = self.builder.get_object('invoice_menu')
			menu.popup(None, None, None, None, event.button, event.time)
			menu.show_all()

	def invoice_history_activated (self, menuitem):
		selection = self.builder.get_object('treeview-selection4')
		model, path = selection.get_selected_rows()
		invoice_id = model[path][0]
		contact_id = model[path][8]
		if not self.invoice_history or self.invoice_history.exists == False:
			from reports import invoice_history as ih
			self.invoice_history = ih.InvoiceHistoryGUI(self.main)
		combo = self.invoice_history.builder.get_object('combobox1')
		combo.set_active_id(contact_id)
		store = self.invoice_history.builder.get_object('invoice_store')
		selection = self.invoice_history.builder.get_object('treeview-selection1')
		selection.unselect_all()
		for row in store:
			if row[0] == invoice_id:
				selection.select_iter(row.iter)
				break
		self.invoice_history.present()

	def product_match_func(self, completion, key, iter):
		split_search_text = key.split()
		for text in split_search_text:
			if text not in self.product_store[iter][1].lower():
				return False# no match
		return True# it's a hit!
		
	def product_changed(self, combo):
		product_id = combo.get_active_id ()
		if product_id == None:
			return
		self.product_id = product_id
		self.populate_product_stores ()

	def product_match_selected (self, completion, model, iter):
		self.product_id = model[iter][0]
		self.populate_product_stores ()

	def populate_product_stores (self):
		self.populate_product_invoices ()
		self.populate_purchase_orders ()
		self.populate_warranty_store ()
		self.populate_manufacturing_store ()

	def populate_warranty_store (self):
		warranty_store = self.builder.get_object('warranty_store')
		warranty_store.clear()
		count = 0
		self.cursor.execute("SELECT "
								"snh.id, "
								"p.name, "
								"sn.serial_number, "
								"snh.date_inserted::text, "
								"format_date(snh.date_inserted), "
								"snh.description, "
								"c.name "
							"FROM serial_number_history AS snh "
							"JOIN serial_numbers AS sn "
							"ON sn.id = snh.serial_number_id "
							"JOIN products AS p ON p.id = sn.product_id "
							"JOIN contacts AS c ON c.id = snh.contact_id "
							"WHERE sn.product_id = %s"
							"ORDER by snh.date_inserted", 
							(self.product_id,))
		for row in self.cursor.fetchall():
			count += 1
			warranty_store.append(row)
		if count == 0:
			self.builder.get_object('label8').set_label('Warranty')
		else:
			label = "<span weight='bold'>Warranty (%s)</span>" % count
			self.builder.get_object('label8').set_markup(label)

	def populate_purchase_orders (self):
		po_store = self.builder.get_object('po_store')
		po_store.clear()
		count = 0
		self.cursor.execute("SELECT "
								"po.id, "
								"date_created::text, "
								"format_date(date_created), "
								"contacts.name, "
								"qty, "
								"price, "
								"order_number "
							"FROM purchase_orders AS po "
							"JOIN purchase_order_line_items AS poli "
							"ON poli.purchase_order_id = po.id "
							"JOIN contacts ON contacts.id = po.vendor_id "
							"WHERE product_id = %s", 
							(self.product_id,))
		for row in self.cursor.fetchall():
			count += 1
			po_store.append(row)
		if count == 0:
			self.builder.get_object('label4').set_label('Purchase Orders')
		else:
			label = "<span weight='bold'>Purchase Orders (%s)</span>" % count
			self.builder.get_object('label4').set_markup(label)

	def populate_product_invoices (self):
		invoice_store = self.builder.get_object('invoice_store')
		invoice_store.clear()
		count = 0
		self.cursor.execute("SELECT "
								"i.id, "
								"dated_for::text, "
								"format_date(dated_for), "
								"i.name, "
								"'Comments: ' || comments, "
								"qty, "
								"price, "
								"c.id::text, "
								"c.name "
							"FROM invoices AS i "
							"JOIN contacts AS c ON c.id = i.customer_id "
							"JOIN invoice_items AS ii ON ii.invoice_id = i.id "
							"WHERE (product_id, i.canceled) = "
							"(%s, False) ORDER BY dated_for", 
							(self.product_id,))
		for row in self.cursor.fetchall():
			count += 1
			invoice_store.append(row)
		if count == 0:
			self.builder.get_object('label2').set_label('Invoices')
		else:
			label = "<span weight='bold'>Invoices (%s)</span>" % count
			self.builder.get_object('label2').set_markup(label)

	def populate_manufacturing_store (self):
		store = self.builder.get_object('manufacturing_store')
		store.clear()
		count = 0
		self.cursor.execute("SELECT "
								"mp.id, "
								"mp.name, "
								"qty, "
								"SUM(stop_time - start_time)::text, "
								"COUNT(DISTINCT(employee_id)) "
							"FROM manufacturing_projects AS mp "
							"JOIN time_clock_projects AS tcp "
								"ON tcp.id = mp.time_clock_projects_id "
							"JOIN time_clock_entries AS tce "
								"ON tce.project_id = tcp.id "
							"WHERE product_id = %s "
							"GROUP BY mp.id, mp.name, qty", (self.product_id,))
		for row in self.cursor.fetchall():
			store.append(row) 
			count+= 1
		if count == 0:
			self.builder.get_object('label3').set_label('Manufacturing')
		else:
			label = "<span weight='bold'>Manufacturing (%s)</span>" % count
			self.builder.get_object('label3').set_markup(label)




			
