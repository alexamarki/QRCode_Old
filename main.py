# Импортируемые библиотеки и модули
import sqlite3
import sys
import qrcode
import urllib.request
import json
import os
import csv
from os.path import expanduser
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PIL.ImageQt import ImageQt
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import *
from qrcode.image.styles.colormasks import *
from uiMainWindow import Ui_MainWindow
from uiHelp import Ui_Dialog as ud
from uiMiniExplorer import Ui_Dialog as imgUd

# Поиск домашней директории пользователя
home = expanduser("~").replace('\\', '/')
if not os.path.exists(f"{home}/QRPhotos/"):
    os.makedirs(f"{home}/QRPhotos/")
# Масштабирование для экранов с большим числом пикселей
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

# Обнуление файла с конфигурациями цветов для генерации кода (т.е. возврат к исходным значениям - белый фон, черный код)
with open('config.json', 'r') as j:
    cfg = json.loads(j.read())
cfg["color"]["colorFG"] = (0, 0, 0)
cfg["color"]["colorBG"] = (255, 255, 255)
data = json.dumps(cfg)
with open('config.json', 'w') as j:
    j.write(data)


class QR(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # Обработка нажатий клавиш в TextBox
        self.prompt.installEventFilter(self)
        # Обработка нажатий на кнопки
        self.codeGenerator.clicked.connect(self.t_prompt)
        self.codeGenerator_data.clicked.connect(self.data_aquisition)
        self.saveButton.clicked.connect(self.save_file_q)
        self.saveCode.clicked.connect(self.save_file)
        self.fileView.clicked.connect(self.table_init)
        self.colorBG.clicked.connect(lambda: configModifier().modifyx_g_color('B'))
        self.colorFG.clicked.connect(lambda: configModifier().modifyx_g_color('F'))
        self.colorSG.clicked.connect(lambda: configModifier().modifyx_g_color('S'))
        self.tabWidget.currentChanged.connect(self.on_tab_change)
        self.promptInclusion.stateChanged.connect(self.on_tab_change)
        self.qrViewer.clicked.connect(self.start_dialog)
        self.helpButton.clicked.connect(self.start_info)
        # Прячем виджеты, которые должны отображаться только при выбранной базе данных на второй странице
        self.stackedWidget.hide()
        self.productInfo.hide()
        # Объвление двух переменных для корректного функционирования программы
        self.pixmap = ''
        self.isTableIn = False
        # Возможность показывать не встроенные диалоговые окна
        self.show()
        # self.progressBar.hide()
        # self.label_6.hide()

    # Диалоги, не встроенные в систему
    # Диалог со всем изображениями, сохраненнми через программу
    def start_dialog(self):
        dlgImg = fileDialog(self)
        dlgImg.exec()

    # Диалог со всеми горячими клавишаии
    def start_info(self):
        dlgInfo = infoDialog(self)
        dlgInfo.exec()

    # Инициализация всех горячих клавиш
    def keyPressEvent(self, event):
        if event.modifiers() == (QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier):
            if event.key() == QtCore.Qt.Key.Key_S:
                self.save_file()
        elif event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            if event.key() == QtCore.Qt.Key.Key_O:
                self.table_init()
                self.tabWidget.setCurrentIndex(1)
            elif event.key() == QtCore.Qt.Key.Key_S:
                self.save_file_q()
            elif event.key() == QtCore.Qt.Key.Key_G:
                if self.tabWidget.currentIndex():
                    self.data_aquisition()
                else:
                    self.t_prompt()
            elif event.key() == QtCore.Qt.Key.Key_Return:
                if self.tabWidget.currentIndex():
                    self.data_aquisition()
                else:
                    self.t_prompt()
        elif event.key() == QtCore.Qt.Key.Key_F1:
            self.start_info()
        elif event.key() == QtCore.Qt.Key.Key_Left:
            self.tabWidget.currentIndex(0)
        elif event.key() == QtCore.Qt.Key.Key_Right:
            self.tabWidget.currentIndex(1)

    # Событие нажатия одной из горячих клавиш внутри поля для ввода текста
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.KeyPress and obj is self.prompt:
            if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier \
                    and event.key() == QtCore.Qt.Key.Key_Return and self.prompt.hasFocus():
                self.t_prompt()
        return super().eventFilter(obj, event)

    # Событие изменения вкладки виджета со вкладками - чтоы менялись даж те элементы, что за его пределами
    def on_tab_change(self):
        if self.isTableIn and self.tabWidget.currentIndex():
            self.stackedWidget.show()
            self.stackedWidget.setCurrentIndex(1)
            if self.promptInclusion.isChecked():
                self.productInfo.show()
            else:
                self.productInfo.hide()
        else:
            self.stackedWidget.hide()
            self.productInfo.hide()

    # Функции сохранения файлов, вызывающие в свою очередь соответсвующие диалоги
    def save_file(self):
        filename = Dialog().file_save_dialog()
        try:
            if self.pixmap:
                self.pixmap.save(filename)
                configModifier().populate_result_csv(filename, os.path.basename(filename))
            else:
                raise EmptyPixmap("The pixmap object attempting to be saved doesn't exist")
        except EmptyPixmap:
            pass

    def save_file_q(self):
        filename = Dialog().file_quick_save_dialog()
        try:
            if self.pixmap:
                self.pixmap.save(f"{home}/QRPhotos/{filename}.jpeg")
                configModifier().populate_result_csv(f"{home}/QRPhotos/{filename}.jpeg", f"{filename}.jpeg")
            else:
                raise EmptyPixmap("The pixmap object attempting to be saved doesn't exist")
        except EmptyPixmap:
            pass
        finally:
            pass

    # Инициализация построения таблицым с базой данных - захват данных из БД
    def table_init(self):
        filename = Dialog().file_choose_dialog_db()
        self.connection = sqlite3.connect(filename)
        try:
            self.fileView.clicked.connect(self.table_build)
            self.plainTextEdit.setPlainText("""SELECT productNames.id, productName, productCategory, productPrice,
                                                    isAvailable, storeName FROM productNames INNER JOIN productPrices ON
                                                    productNames.id == productPrices.nameID INNER JOIN 
                                                    productAvailability ON productPrices.nameID == 
                                                    productAvailability.nameID""")
            self.stackedWidget.show()
            self.stackedWidget.setCurrentIndex(1)
            self.table_build()
        except sqlite3.OperationalError:
            self.stackedWidget.setCurrentIndex(0)
            self.stackedWidget.hide()

    # Построение самой таблицы в интерфейсе
    def table_build(self):
        query = self.plainTextEdit.toPlainText()
        res = self.connection.cursor().execute(query).fetchall()
        self.database.setColumnCount(6)
        self.database.setRowCount(0)
        self.database.setHorizontalHeaderLabels(['id', 'Name', 'Category', 'Price (₽)', 'Availability', 'Storefront'])
        self.database.setColumnHidden(0, True)
        for i, row in enumerate(res):
            self.database.setRowCount(self.database.rowCount() + 1)
            for j, elem in enumerate(row):
                self.database.setItem(i, j, QTableWidgetItem(str(elem)))
        self.isTableIn = True
        self.database.horizontalHeader().setStretchLastSection(True)
        self.database.horizontalHeader().stretchSectionCount()
        self.on_tab_change()  # повторная проверка на то, отмечена ли галочка include prompt

    # Получение, в зависимости от значения productInfo, либо ссылки на продукт и его изображение,
    # либо на еще и остальные данные о продукте
    def data_aquisition(self):
        # self.progressBar.setValue(0)
        # self.progressBar.show()
        # self.label_6.show()
        rowNumber = self.database.currentRow()
        try:
            if self.database.item(rowNumber, 0):
                item = self.database.item(rowNumber, 0).text()
                linkQuery = f"SELECT productLink FROM productMedia WHERE productMedia.nameID == {item}"
                link = self.connection.cursor().execute(linkQuery).fetchall()
                if self.promptInclusion.isChecked():
                    imageQuery = f"SELECT imageLink FROM productMedia WHERE productMedia.nameID == {item}"
                    imageLink = self.connection.cursor().execute(imageQuery).fetchall()
                    painter, image = self.build_image(link[0], 722, 361)
                    if not self.productInfo.currentIndex():
                        priceQuery = f"SELECT productPrice FROM productPrices WHERE productPrices.nameID == {item}"
                        price = self.connection.cursor().execute(priceQuery).fetchall()[0][0] + " ₽"
                        nameQuery = f"SELECT productName FROM productNames WHERE productNames.id == {item}"
                        name = self.connection.cursor().execute(nameQuery).fetchall()[0][0]
                        catQuery = f"SELECT productCategory FROM productNames WHERE productNames.id == {item}"
                        cat = self.connection.cursor().execute(catQuery).fetchall()[0][0]
                        avaQuery = f"""SELECT isAvailable FROM productAvailability WHERE productAvailability.nameID 
                        == {item}"""
                        ava = self.connection.cursor().execute(avaQuery).fetchall()[0][0]
                        if ava == "✓":
                            ava = "In Stock"
                        else:
                            ava = "Out of Stock"
                        sfQuery = f"""SELECT storeName FROM productAvailability WHERE productAvailability.nameID 
                        == {item}"""
                        sf = self.connection.cursor().execute(sfQuery).fetchall()[0][0]
                        self.d_prompt(painter, imageLink=imageLink[0], image=image, price=price, name=name, cat=cat,
                                      ava=ava, sf=sf)
                    else:
                        self.d_prompt(painter, imageLink=imageLink[0], image=image)
                else:
                    self.t_prompt(link)
            else:
                raise EmptyGenPrompt("There is no table item to generate a code for")
        except EmptyGenPrompt:
            pass

    # Рисование изображения на основании прошлых запросов (для тех слуаев, где есть картинка, дл остальных - t_prompt
    def d_prompt(self, painter, imageLink, image, price='', name='', cat='', ava='', sf=''):
        if not self.productInfo.currentIndex():
            self.url_pic_builder(imageLink[0], painter, 175, 381, 10)
            self.text_builder("Arial", 24, painter, name, 381, 200, 321, 120,
                              QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop |
                              QtCore.Qt.TextFlag.TextWordWrap, weight=400)
            self.text_builder('Arial Black', 15, painter, price, 576, 70, 136, 70,
                              QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop |
                              QtCore.Qt.TextFlag.TextWordWrap)
            self.text_builder("Arial", 10, painter, cat, 576, 40, 136, 20,
                              QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter |
                              QtCore.Qt.TextFlag.TextWordWrap)
            self.text_builder("Arial", 10, painter, ava, 576, 130, 136, 20,
                              QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
            self.text_builder("Arial", 10, painter, sf, 381, 340, 331, 10,
                              QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter, weight=500)
        else:
            self.url_pic_builder(imageLink[0], painter, 300, 370, 50)
        painter.end()
        # self.progressBar.setValue(100)
        self.pixmap = QPixmap.fromImage(image)
        self.label_5.setPixmap(self.pixmap)
        # self.progressBar.hide()
        # self.label_6.hide()

    # Получение данных для запроса в том случае, если генерируется только код на квадратной картинке/код + текст,
    # введенный в соответсвующее поле на первой вкладке
    def t_prompt(self, text=''):
        # self.progressBar.setValue(0)
        # self.progressBar.show()
        # self.label_6.show()
        if not text:
            text = self.prompt.toPlainText()
        if self.promptInclusion.isChecked():  # Включаем текстовый запрос в картинку
            painter, image = self.build_image(text, 722, 361)
            self.text_builder("Arial", 16, painter, text, 371, 10, 341, 341,
                              QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter |
                              QtCore.Qt.TextFlag.TextWordWrap)
            painter.end()
        else:  # Генерируем картинку, состоящую чисто из кода
            painter, image = self.build_image(text, 361, 361)
            painter.end()
        # self.progressBar.setValue(100)
        self.pixmap = QPixmap.fromImage(image)
        self.label_5.setPixmap(self.pixmap)
        # self.progressBar.hide()
        # self.label_6.hide()

    # Рисование самого колста для изображеня и QR-объекта на нем
    def build_image(self, linklink, canvasX, canvasY):
        image = QImage(canvasX, canvasY, QImage.Format.Format_RGB16)
        image.fill(QtGui.QColor("white"))
        painter = QPainter()
        painter.begin(image)
        self.create_qr_object(painter, linklink, 361)
        return painter, image

    # Создание QR-объекта с выбранными пользователем характеристиками
    def create_qr_object(self, painter, text, sqSize):
        qr_i = qrcode.QRCode()
        qr_i.add_data(text)
        with open('config.json') as f:
            cfg = json.load(f)
        BGcol = tuple(cfg['color']['colorBG'])
        FGcol = tuple(cfg['color']['colorFG'])
        SDcol = tuple(cfg['color']['colorSG'])
        if BGcol == (0, 0, 0):
            BGcol = (0, 0, 1)
        module_drawers = [SquareModuleDrawer(), GappedSquareModuleDrawer(), CircleModuleDrawer(),
                          RoundedModuleDrawer(), VerticalBarsDrawer(), HorizontalBarsDrawer()]
        color_masks = [SolidFillColorMask(back_color=BGcol, front_color=FGcol),
                       RadialGradiantColorMask(back_color=BGcol, center_color=FGcol, edge_color=SDcol),
                       SquareGradiantColorMask(back_color=BGcol, center_color=FGcol, edge_color=SDcol),
                       HorizontalGradiantColorMask(back_color=BGcol, left_color=FGcol, right_color=SDcol),
                       VerticalGradiantColorMask(back_color=BGcol, top_color=FGcol, bottom_color=SDcol)]
        qr_image = qr_i.make_image(image_factory=StyledPilImage, error_correction=qrcode.constants.ERROR_CORRECT_H,
                                   module_drawer=module_drawers[self.codeFormatting.currentIndex()],
                                   color_mask=color_masks[self.colorMasking.currentIndex()])
        IQObj = ImageQt(qr_image)
        QIObj = QtGui.QImage(IQObj)
        sense = QIObj.scaled(sqSize, sqSize, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        painter.drawImage(QtCore.QRect(0, 0, sqSize, sqSize), sense)

    # Постороение картинки при наличии на нее ссылки в интернете
    def url_pic_builder(self, url, painter, imageBounds, x, y):
        urlIMG = QtGui.QImage()
        try:
            data = urllib.request.urlopen(url).read()
            urlIMG.loadFromData(data)
        except Exception:
            urlIMG.load('LinkError')
        urlIMG = urlIMG.scaled(imageBounds, imageBounds, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        painter.drawImage(QtCore.QRect(x, y, urlIMG.width(), urlIMG.height()), urlIMG)

    # Построение текста
    def text_builder(self, family, fS, painter, text, x, y, w, h, flags, weight=''):
        font = QtGui.QFont()
        font.setFamily(family)
        font.setPointSize(fS)
        if weight:
            font.setWeight(weight)
        painter.setFont(font)
        painter.drawText(x, y, w, h, flags, text)

    def closeEvent(self, event):
        self.connection.close()


# Класс, необходимый для получения данных из встроенных диалоговых окон без силього засорения других функций
class Dialog():
    # Диалог для выбора цвета
    def color_dialog(self):
        color = QColorDialog.getColor()
        red = color.red()
        green = color.green()
        blue = color.blue()
        return red, green, blue

    # Диалог для выюора пути, имени и расширения сохраняемого файла
    def file_save_dialog(self):
        home_dir = str(home)
        filename = (QFileDialog.getSaveFileName(None, 'Save as', home_dir,
                                                """Compressed Image (*.jpeg);;Image (*.png);;BMP Image 
                                                (*.bmp);;All Files (*)"""))[0]
        return filename

    # Диалог для выбора имени файаа для сохранения его в дефолтную папку программы с расширением jpeg
    def file_quick_save_dialog(self):
        filename = (QInputDialog.getText(None, "Save", "Input filename"))[0]
        return filename

    # Диалог для выбора файла базы данных для его открытия
    def file_choose_dialog_db(self):
        home_dir = str(home)
        filename = QFileDialog.getOpenFileName(None, 'Choose a database file', home_dir, 'Database (*.db)')
        return filename[0]


# Диалоговое окно, отображающее версию программы и все горячие клавиши (сам по себе может быть вызван F1
class infoDialog(QDialog, ud):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Help")


# Диалоговое окно для просмотра изображений, сохраненных через эту программу
class fileDialog(QDialog, imgUd):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("All saved QREncoder QR Codes")
        self.imgDisplay.itemDoubleClicked.connect(self.open_file)
        self.table_populator()

    def table_populator(self):
        with open('display.csv', 'r', encoding="utf8") as imageFile:
            reader = list(csv.reader(imageFile, delimiter=';', quotechar='"'))
            for i in reader:
                self.imgDisplay.addItem(QListWidgetItem(QIcon(i[0]), i[1]))

    def open_file(self):
        with open('display.csv', 'r', encoding="utf8") as imageFile:
            reader = list(csv.reader(imageFile, delimiter=';', quotechar='"'))
        os.startfile(reader[self.imgDisplay.currentRow()][0])


# Класс для модификации различных файлов, на которых оперирует программа - в данном случае это json (первые две ф-ции)
# и csv - третья функция
class configModifier():
    # Функция для изменения цвета фона/кода/градиента
    def modifyx_g_color(self, ground):
        colorCar = Dialog().color_dialog()
        with open('config.json', 'r') as j:
            cfg = json.loads(j.read())
        cfg["color"][f"color{ground}G"] = colorCar
        data = json.dumps(cfg)
        with open('config.json', 'w') as j:
            j.write(data)

    # Функция для изменения прочих элементов файла json - изначально должна была использоваться как минимум для
    # хранения пути к изображение, которое мы хотим поставить вместо цвета QR-кода, но в связи с тем,
    # что данный функционал не было готов к релизу, функция не используется
    def config_temp(self, key, value):
        with open('config.json', 'r') as j:
            cfg = json.loads(j.read())
        cfg[key] = value
        data = json.dumps(cfg)
        with open('config.json', 'w') as j:
            j.write(data)

    # Функция для добавления в csv файл пути до картинки и имени ее файла - необходимо для
    # отображения в отдельном диалоговом окне
    def populate_result_csv(self, path, filename):
        with open('display.csv', 'a', newline='', encoding="utf8") as newFile:
            editor = csv.writer(newFile, delimiter=';', quotechar='"')
            editor.writerow([path, filename])


# Исключение, вызываемое при отсутсвии кода для сохранения в файл
class EmptyPixmap(Exception):
    pass


# Исключение, вызываемое при отсутствии выбора ячейки базы данных, на основе которой можно сделать код
class EmptyGenPrompt(Exception):
    pass


# Хук, позволяет приложениям на QT не вылетать при каждой ошибке
def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    strt = QR()
    strt.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())
