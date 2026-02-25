import sys
import os
import datetime
from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QFileDialog, QTreeWidgetItem, QMessageBox, QStyle
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

class FolderDiffChecker(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # Chargement du nouveau fichier UI
        try:
            uic.loadUi('main.ui', self)
        except Exception as e:
            print(f"Erreur de chargement UI: {e}")
        
        # Configuration des colonnes
        self.treeWidget.setColumnCount(4)
        self.treeWidget.setHeaderLabels(["Structure / Fichiers", "Taille (Octets)", "Modifié le", "Diagnostic"])
        self.treeWidget.setColumnWidth(0, 350)

        # Connexions des boutons
        self.btn_select_a.clicked.connect(lambda: self.select_root('A'))
        self.btn_select_b.clicked.connect(lambda: self.select_root('B'))
        self.btn_compare.clicked.connect(self.compare_folders)
        self.btn_export.clicked.connect(self.export_report)
        
        # Nouveau bouton : Déplier Tout
        if hasattr(self, 'btn_expand_all'):
            self.btn_expand_all.clicked.connect(self.treeWidget.expandAll)

        # Menu contextuel clic droit
        self.treeWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.treeWidget.customContextMenuRequested.connect(self.open_context_menu)

        self.root_a = ""
        self.root_b = ""

    def select_root(self, side):
        path = QFileDialog.getExistingDirectory(self, f"Sélectionner le dossier {side}")
        if path:
            if side == 'A':
                self.root_a = path
                self.lbl_path_a.setText(path)
            else:
                self.root_b = path
                self.lbl_path_b.setText(path)

    def compare_folders(self):
        if not self.root_a or not self.root_b:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner les deux dossiers.")
            return

        self.treeWidget.clear()
        stats = {"total": 0, "identique": 0, "divergent": 0, "manquant": 0}
        
        items_a = {d for d in os.listdir(self.root_a) if os.path.isdir(os.path.join(self.root_a, d))}
        items_b = {d for d in os.listdir(self.root_b) if os.path.isdir(os.path.join(self.root_b, d))}
        all_items = sorted(items_a | items_b)

        icon_warn = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
        icon_err = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
        icon_ok = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)

        for name in all_items:
            stats["total"] += 1
            parent_item = QTreeWidgetItem(self.treeWidget)
            parent_item.setText(0, name)
            parent_item.setFont(0, self.get_bold_font())

            p_a = os.path.join(self.root_a, name)
            p_b = os.path.join(self.root_b, name)

            # CAS 1 : Dossier présent des deux côtés
            if name in items_a and name in items_b:
                files_a = set(os.listdir(p_a))
                files_b = set(os.listdir(p_b))
                size_diff = False
                
                for f in sorted(files_a | files_b):
                    child = QTreeWidgetItem(parent_item)
                    child.setText(0, f)
                    f_a, f_b = os.path.join(p_a, f), os.path.join(p_b, f)
                    
                    if os.path.exists(f_a) and os.path.exists(f_b):
                        s_a, s_b = os.path.getsize(f_a), os.path.getsize(f_b)
                        child.setText(1, f"{s_a} | {s_b}")
                        if s_a != s_b:
                            child.setText(3, "⚠️ Taille divergente")
                            child.setForeground(3, QColor("#f1c40f"))
                            size_diff = True
                        else:
                            child.setText(3, "✅ Identique")
                    elif os.path.exists(f_a):
                        child.setText(3, "❌ Absent de la Cible")
                        child.setForeground(3, QColor("#e74c3c"))
                    else:
                        child.setText(3, "➕ Nouveau (Absent Source)")

                count_a, count_b = len(files_a), len(files_b)
                status_txt = f"OK ({count_a} vs {count_b} fichiers)"
                if count_a == count_b:
                    if size_diff:
                        parent_item.setText(3, f"✅ {status_txt} ⚠️")
                        parent_item.setForeground(3, QColor("#85e085"))
                        parent_item.setIcon(0, icon_warn)
                        stats["divergent"] += 1
                    else:
                        parent_item.setText(3, f"✅ {status_txt}")
                        parent_item.setForeground(3, QColor("#2ecc71"))
                        parent_item.setIcon(0, icon_ok)
                        stats["identique"] += 1
                else:
                    parent_item.setText(3, f"❌ Contenu différent ({count_a} vs {count_b})")
                    parent_item.setForeground(3, QColor("#e74c3c"))
                    parent_item.setIcon(0, icon_err)
                    stats["manquant"] += 1

            # CAS 2 : Dossier orphelin (Affiche quand même le contenu)
            else:
                exists_in = "SOURCE" if name in items_a else "CIBLE"
                missing_in = "CIBLE" if name in items_a else "SOURCE"
                path_exists = p_a if name in items_a else p_b
                
                parent_item.setText(3, f"❌ INEXISTANT DANS {missing_in}")
                parent_item.setForeground(3, QColor("#e74c3c"))
                parent_item.setIcon(0, icon_err)
                stats["manquant"] += 1

                for f in sorted(os.listdir(path_exists)):
                    child = QTreeWidgetItem(parent_item)
                    child.setText(0, f)
                    child.setText(3, f"Exclusif à {exists_in}")
                    child.setForeground(3, QColor("#bac2de"))

        self.update_dashboard(stats)

    def update_dashboard(self, s):
        self.lbl_stat_total.setText(f"Dossiers: {s['total']}")
        self.lbl_stat_ok.setText(f"Parfait: {s['identique']}")
        self.lbl_stat_div.setText(f"Divergences: {s['divergent']}")
        self.lbl_stat_err.setText(f"Alertes: {s['manquant']}")

    def get_bold_font(self):
        f = QFont(); f.setBold(True); return f

    def open_context_menu(self, pos):
        item = self.treeWidget.itemAt(pos)
        if not item: return
        menu = QtWidgets.QMenu()
        a1 = menu.addAction("📂 Ouvrir Source")
        a2 = menu.addAction("📂 Ouvrir Cible")
        action = menu.exec(self.treeWidget.viewport().mapToGlobal(pos))
        name = item.parent().text(0) if item.parent() else item.text(0)
        if action == a1: os.startfile(os.path.join(self.root_a, name))
        if action == a2: os.startfile(os.path.join(self.root_b, name))

    def export_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Rapport", "diff_report.txt", "*.txt")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"DIFF FOLDER CHECKER REPORT - {datetime.datetime.now()}\n\n")
                for i in range(self.treeWidget.topLevelItemCount()):
                    it = self.treeWidget.topLevelItem(i)
                    f.write(f"[{it.text(0)}] {it.text(3)}\n")
            QMessageBox.information(self, "Export", "Rapport exporté.")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = FolderDiffChecker()
    window.show()
    sys.exit(app.exec())
