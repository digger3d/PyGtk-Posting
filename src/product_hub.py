# product_hub.py
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

from gi.repository import Gtk, Gdk, GLib
import main

UI_FILE = main.ui_directory + "/product_hub.ui"

class ProductHubGUI:
	def __init__(self, main, product_id):

		self.builder = Gtk.Builder()
		self.builder.add_from_file(UI_FILE)
		self.builder.connect_signals(self)

		self.main = main
		self.db = main.db
		self.product_id = product_id
		self.cursor = self.db.cursor()
		self.cursor.execute ("SELECT name FROM products WHERE id = %s", (product_id,))
		self.name = self.cursor.fetchone()[0]
		self.builder.get_object('label1').set_label(self.name)
		self.window = self.builder.get_object('window1')
		self.window.show_all()

	def destroy (self, window):
		self.cursor.close()

	def cancel_clicked (self, button):
		self.window.destroy()

	def edit_product_clicked (self, button):
		import products
		p = products.ProductsGUI (self.main)
		p.select_product (self.product_id)
		self.window.destroy()

	def product_location_clicked (self, button):
		import product_location
		p = product_location.ProductLocationGUI(self.main)
		p.builder.get_object('searchentry1').set_text(self.name)
		self.window.destroy()

	def product_transactions_clicked (self, button):
		from reports import product_transactions
		product_transactions.ProductTransactionsGUI(self.main, self.product_id)
		self.window.destroy()

	def product_search_clicked (self, button):
		import product_search
		p = product_search.ProductSearchGUI(self.main)
		p.builder.get_object('searchentry1').set_text(self.name)
		self.window.destroy()

	def product_history_clicked (self, button):
		from reports import product_history
		p = product_history.ProductHistoryGUI(self.main)
		p.builder.get_object('combobox1').set_active_id (str(self.product_id))
		self.window.destroy()
		


		
