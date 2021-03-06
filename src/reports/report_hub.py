# report_hub.py
#
# Copyright (C) 2019 - house
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
import main

UI_FILE = main.ui_directory + "/reports/report_hub.ui"

class ReportHubGUI (Gtk.Builder):
	def __init__(self, treeview):

		Gtk.Builder.__init__ (self)
		self.add_from_file (UI_FILE)
		self.connect_signals(self)
		if treeview.get_allocated_width() > 742:
			self.get_object("error_label").set_no_show_all(False)
		self.window = self.get_object("window")
		self.window.show_all()
		self.treeview = treeview

	def pdf_export_clicked (self, button):
		from reports import export_to_pdf
		export_to_pdf.ExportToPdfGUI(self.treeview)
		self.window.destroy()

	def xls_export_clicked (self, button):
		from reports import export_to_xls
		export_to_xls.ExportToXlsGUI(self.treeview)
		self.window.destroy()

	def cancel_clicked (self, button):
		self.window.destroy()



