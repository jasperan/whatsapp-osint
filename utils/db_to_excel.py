from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
import sqlite3
import os

class Converter:
    DB_PATH = 'database/victims_logs.db'
    EXCEL_FILE = 'History_wp.xlsx'

    def db_to(self):
        """Inicializa la conexión a la base de datos y crea el libro de Excel."""
        self.conn = sqlite3.connect(self.DB_PATH)
        self.cursor = self.conn.cursor()
        self.wb = Workbook()
        self.ws = self.wb.active

    def db_to_excel(self):
        """Exporta los datos de la base de datos a un archivo Excel."""
        # Estilos
        bold = Font(bold=True, name='Arial', color="00800000", size=10)
        align = Alignment(horizontal="center")

        # Configuración de columnas
        headers = [
            ("A", 15, "Id"),
            ("B", 17, "Username"),
            ("C", 15, "DateTime"),
            ("D", 15, "Hour"),
            ("E", 15, "Minutes"),
            ("F", 15, "Second"),
            ("G", 17, "Type_Connection"),
            ("H", 15, "Online Time")
        ]
        
        for col, width, title in headers:
            self.ws.column_dimensions[col].width = width
            cell = self.ws[f"{col}1"]
            cell.font = bold
            cell.alignment = align
            cell.value = title

        self.ws.title = "History Of Their Wp"

        try:
            self.cursor.execute("SELECT * FROM Connections ORDER BY date DESC")
            all_data = self.cursor.fetchall()

            for data in all_data:
                self.ws.append(data)
            print("All data added to your Excel file")
            self.wb.save(self.EXCEL_FILE)

        except PermissionError:
            print(f"Please close '{self.EXCEL_FILE}' and restart the program.")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            self.conn.close()

if __name__ == '__main__':
    converter = Converter()
    converter.db_to()
    converter.db_to_excel()