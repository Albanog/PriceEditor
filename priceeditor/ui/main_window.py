from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.excel_import import import_excel, merge_import
from ..core.models import GlobalSettings, Product
from ..core.pdf_generator import fmt_ars, generate_pdf
from ..core.pricing import compute_prices
from ..core.project_io import load_project, save_project

COL_CHECK = 0
COL_NAME = 1
COL_USD = 2
COL_CUOTAS_N = 3
COL_TIPO_COBRO = 4
COL_CONTADO = 5
COL_CUOTA = 6
COL_COPIES = 7
COL_DELETE = 8
COLUMNS = [
    "", "Producto", "USD", "N Cuotas", "Tipo de cobro (opcional)",
    "Contado ARS", "Cuota ARS", "Copias", "",
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PriceEditor")
        self.resize(1200, 700)

        self.products: list[Product] = []
        self.settings = GlobalSettings()
        self.current_project_path: str | None = None

        self._build_ui()

    # ---------- UI construction ----------

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        layout.addLayout(self._build_toolbar())
        layout.addLayout(self._build_settings_bar())
        layout.addLayout(self._build_filter_bar())

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(COL_NAME, 260)
        self.table.setColumnWidth(COL_TIPO_COBRO, 220)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        layout.addWidget(self.table)

        self.header_check_all = QCheckBox(self.table.horizontalHeader())
        self.header_check_all.setTristate(False)
        self.header_check_all.stateChanged.connect(self._on_header_check_changed)
        self._position_header_checkbox()
        self.table.horizontalHeader().sectionResized.connect(lambda *_: self._position_header_checkbox())

        show_deleted_row = QHBoxLayout()
        self.show_deleted_chk = QCheckBox("Mostrar eliminados")
        self.show_deleted_chk.stateChanged.connect(self.refresh_table)
        show_deleted_row.addWidget(self.show_deleted_chk)
        show_deleted_row.addStretch()
        layout.addLayout(show_deleted_row)

        self.setCentralWidget(central)

    def _build_toolbar(self) -> QHBoxLayout:
        row = QHBoxLayout()

        btn_new = QPushButton("Nuevo proyecto")
        btn_new.clicked.connect(self.on_new_project)
        row.addWidget(btn_new)

        btn_import = QPushButton("Importar Excel")
        btn_import.clicked.connect(self.on_import_excel)
        row.addWidget(btn_import)

        btn_add = QPushButton("Agregar producto")
        btn_add.clicked.connect(self.on_add_product)
        row.addWidget(btn_add)

        btn_open = QPushButton("Abrir proyecto")
        btn_open.clicked.connect(self.on_open_project)
        row.addWidget(btn_open)

        btn_save = QPushButton("Guardar proyecto")
        btn_save.clicked.connect(self.on_save_project)
        row.addWidget(btn_save)

        btn_save_as = QPushButton("Guardar como...")
        btn_save_as.clicked.connect(self.on_save_project_as)
        row.addWidget(btn_save_as)

        row.addStretch()

        btn_generate = QPushButton("Generar PDF")
        btn_generate.clicked.connect(self.on_generate_pdf)
        row.addWidget(btn_generate)

        return row

    def _build_settings_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()

        row.addWidget(QLabel("Cotizacion (ARS por USD):"))
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0, 10_000_000)
        self.rate_spin.setDecimals(2)
        self.rate_spin.setValue(self.settings.exchange_rate)
        self.rate_spin.valueChanged.connect(self.on_settings_changed)
        row.addWidget(self.rate_spin)

        row.addWidget(QLabel("Recargo cuotas %:"))
        self.pct_spin = QDoubleSpinBox()
        self.pct_spin.setRange(0, 500)
        self.pct_spin.setDecimals(2)
        self.pct_spin.setValue(self.settings.cuotas_pct)
        self.pct_spin.valueChanged.connect(self.on_settings_changed)
        row.addWidget(self.pct_spin)

        row.addWidget(QLabel("Cuotas por defecto:"))
        self.default_cuotas_spin = QSpinBox()
        self.default_cuotas_spin.setRange(0, 24)
        self.default_cuotas_spin.setValue(self.settings.default_cuotas_count)
        self.default_cuotas_spin.valueChanged.connect(self.on_settings_changed)
        row.addWidget(self.default_cuotas_spin)

        row.addWidget(QLabel("Redondeo:"))
        self.rounding_spin = QSpinBox()
        self.rounding_spin.setRange(1, 100000)
        self.rounding_spin.setValue(self.settings.rounding_step)
        self.rounding_spin.valueChanged.connect(self.on_settings_changed)
        row.addWidget(self.rounding_spin)

        row.addStretch()
        return row

    def _build_filter_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("Filtrar:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Buscar producto")
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(250)
        self.filter_timer.timeout.connect(self.refresh_table)
        self.filter_edit.textChanged.connect(lambda: self.filter_timer.start())
        row.addWidget(self.filter_edit)
        return row

    # ---------- settings ----------

    def on_settings_changed(self) -> None:
        self.settings.exchange_rate = self.rate_spin.value()
        self.settings.cuotas_pct = self.pct_spin.value()
        self.settings.default_cuotas_count = self.default_cuotas_spin.value()
        self.settings.rounding_step = self.rounding_spin.value()
        self._update_price_columns()

    def on_set_all_checked(self, checked: bool) -> None:
        for p in self._visible_products():
            p.checked = checked
        self.refresh_table()

    # ---------- import / project ----------

    def on_import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Importar Excel", "", "Excel (*.xlsx *.xls)")
        if not path:
            return
        try:
            rows = import_excel(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer el archivo:\n{e}")
            return
        self.products = merge_import(self.products, rows)
        self.refresh_table()

    def on_new_project(self) -> None:
        if self.products:
            reply = QMessageBox.question(
                self, "Nuevo proyecto",
                "Se perderan los cambios no guardados. Continuar?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.products = []
        self.settings = GlobalSettings()
        self.current_project_path = None
        self._sync_settings_widgets()
        self.refresh_table()

    def on_add_product(self) -> None:
        self.products.append(Product(name="Nuevo producto", usd_price=0.0))
        self.show_deleted_chk.setChecked(False)
        self.refresh_table()
        self.table.scrollToBottom()

    def on_open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Abrir proyecto", "", "PriceEditor (*.pep.json)")
        if not path:
            return
        try:
            self.products, self.settings = load_project(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el proyecto:\n{e}")
            return
        self.current_project_path = path
        self._sync_settings_widgets()
        self.refresh_table()

    def on_save_project(self) -> None:
        path = self.current_project_path
        if not path:
            self.on_save_project_as()
            return
        try:
            save_project(path, self.products, self.settings)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{e}")
            return
        self.current_project_path = path

    def on_save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Guardar proyecto como", "", "PriceEditor (*.pep.json)")
        if not path:
            return
        if not path.endswith(".pep.json"):
            path += ".pep.json"
        try:
            save_project(path, self.products, self.settings)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{e}")
            return
        self.current_project_path = path

    def _sync_settings_widgets(self) -> None:
        for spin in (self.rate_spin, self.pct_spin, self.default_cuotas_spin, self.rounding_spin):
            spin.blockSignals(True)
        self.rate_spin.setValue(self.settings.exchange_rate)
        self.pct_spin.setValue(self.settings.cuotas_pct)
        self.default_cuotas_spin.setValue(self.settings.default_cuotas_count)
        self.rounding_spin.setValue(self.settings.rounding_step)
        for spin in (self.rate_spin, self.pct_spin, self.default_cuotas_spin, self.rounding_spin):
            spin.blockSignals(False)

    # ---------- table ----------

    def _visible_products(self) -> list[Product]:
        products = self.products if self.show_deleted_chk.isChecked() else [
            p for p in self.products if not p.deleted
        ]
        words = self.filter_edit.text().lower().split()
        if words:
            products = [p for p in products if all(w in p.name.lower() for w in words)]
        return products

    def refresh_table(self) -> None:
        self.table.blockSignals(True)
        visible = self._visible_products()
        self.table.setRowCount(len(visible))

        self.header_check_all.blockSignals(True)
        self.header_check_all.setChecked(bool(visible) and all(p.checked for p in visible))
        self.header_check_all.blockSignals(False)

        for row_idx, product in enumerate(visible):
            chk = QCheckBox()
            chk.setChecked(product.checked)
            chk.stateChanged.connect(lambda state, p=product: self._on_check_changed(p, state))
            self.table.setCellWidget(row_idx, COL_CHECK, chk)

            name_item = QTableWidgetItem(product.name)
            self.table.setItem(row_idx, COL_NAME, name_item)

            usd_item = QTableWidgetItem(f"{product.usd_price:.2f}")
            self.table.setItem(row_idx, COL_USD, usd_item)

            cuotas_n_item = QTableWidgetItem(
                str(product.cuotas_count) if product.cuotas_count is not None else ""
            )
            self.table.setItem(row_idx, COL_CUOTAS_N, cuotas_n_item)

            tipo_item = QTableWidgetItem(product.tipo_cobro_text or "")
            self.table.setItem(row_idx, COL_TIPO_COBRO, tipo_item)

            contado, cuota, _n = compute_prices(product, self.settings)
            contado_item = QTableWidgetItem(fmt_ars(contado))
            if product.override_contado_ars is not None:
                contado_item.setBackground(Qt.yellow)
                contado_item.setForeground(Qt.black)
            self.table.setItem(row_idx, COL_CONTADO, contado_item)

            cuota_item = QTableWidgetItem(fmt_ars(cuota))
            if product.override_cuota_ars is not None:
                cuota_item.setBackground(Qt.yellow)
                cuota_item.setForeground(Qt.black)
            self.table.setItem(row_idx, COL_CUOTA, cuota_item)

            copies_item = QTableWidgetItem(str(product.copies))
            self.table.setItem(row_idx, COL_COPIES, copies_item)

            btn = QPushButton("Restaurar" if product.deleted else "Eliminar")
            btn.clicked.connect(lambda _, p=product: self._on_toggle_delete(p))
            self.table.setCellWidget(row_idx, COL_DELETE, btn)

        self.table.blockSignals(False)
        try:
            self.table.itemChanged.disconnect(self._on_item_changed)
        except (TypeError, RuntimeError):
            pass
        self.table.itemChanged.connect(self._on_item_changed)

    def _position_header_checkbox(self) -> None:
        header = self.table.horizontalHeader()
        x = header.sectionPosition(COL_CHECK)
        w = header.sectionSize(COL_CHECK)
        size = self.header_check_all.sizeHint()
        self.header_check_all.move(
            x + (w - size.width()) // 2, (header.height() - size.height()) // 2
        )

    def _on_header_check_changed(self, state: int) -> None:
        checked = state == 2  # Qt.CheckState.Checked
        for p in self._visible_products():
            p.checked = checked
        self.refresh_table()

    def _update_price_columns(self) -> None:
        self.table.blockSignals(True)
        visible = self._visible_products()
        for row_idx, product in enumerate(visible):
            contado, cuota, _n = compute_prices(product, self.settings)

            contado_item = self.table.item(row_idx, COL_CONTADO)
            contado_item.setText(fmt_ars(contado))
            if product.override_contado_ars is not None:
                contado_item.setBackground(Qt.yellow)
                contado_item.setForeground(Qt.black)
            else:
                contado_item.setBackground(Qt.white)
                contado_item.setForeground(Qt.black)

            cuota_item = self.table.item(row_idx, COL_CUOTA)
            cuota_item.setText(fmt_ars(cuota))
            if product.override_cuota_ars is not None:
                cuota_item.setBackground(Qt.yellow)
                cuota_item.setForeground(Qt.black)
            else:
                cuota_item.setBackground(Qt.white)
                cuota_item.setForeground(Qt.black)
        self.table.blockSignals(False)

    def _on_check_changed(self, product: Product, state: int) -> None:
        product.checked = state == 2  # Qt.CheckState.Checked

    def _on_toggle_delete(self, product: Product) -> None:
        product.deleted = not product.deleted
        self.refresh_table()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        row = item.row()
        visible = self._visible_products()
        if row >= len(visible):
            return
        product = visible[row]
        col = item.column()
        text = item.text().strip()

        if col == COL_NAME:
            product.name = text
        elif col == COL_USD:
            try:
                product.usd_price = float(text.replace(",", "."))
            except ValueError:
                pass
        elif col == COL_CUOTAS_N:
            if text == "":
                product.cuotas_count = None
            else:
                try:
                    product.cuotas_count = int(text)
                except ValueError:
                    pass
        elif col == COL_TIPO_COBRO:
            product.tipo_cobro_text = text or None
        elif col == COL_CONTADO:
            self._set_override(product, "override_contado_ars", text)
        elif col == COL_CUOTA:
            self._set_override(product, "override_cuota_ars", text)
        elif col == COL_COPIES:
            try:
                product.copies = max(1, int(text))
            except ValueError:
                pass

        self._update_price_columns()

    def _set_override(self, product: Product, attr: str, text: str) -> None:
        cleaned = text.replace("$", "").replace(".", "").strip()
        if cleaned == "":
            setattr(product, attr, None)
            return
        try:
            setattr(product, attr, float(cleaned))
        except ValueError:
            pass

    # ---------- pdf ----------

    def on_generate_pdf(self) -> None:
        checked = [p for p in self.products if p.checked and not p.deleted]
        if not checked:
            QMessageBox.warning(self, "Nada para generar", "No hay productos marcados.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", "carteles.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            generate_pdf(self.products, self.settings, path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar el PDF:\n{e}")
            return
        QMessageBox.information(self, "Listo", f"PDF generado:\n{path}")
