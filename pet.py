# -*- coding: utf-8 -*-
"""桌面宠物:比目鱼博士

操作:
  左键单击   -> 跳跃 + 随机说话气泡
  按住左键拖 -> 移动位置(带晃动效果)
  鼠标滚轮   -> 放大 / 缩小
  右键单击   -> 菜单(交互 / 缩放 / 重置 / 置顶 / 退出)
"""
import os
import sys
import random
from PyQt5.QtWidgets import QApplication, QWidget, QMenu, QLabel, QMessageBox
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve

# --------------------------配置区--------------------------
MIN_SCALE = 0.20
MAX_SCALE = 2.20
INIT_SCALE = 0.40
BUBBLE_DURATION = 2500   # 气泡显示毫秒
JUMP_DURATION = 2500
SHAKE_PAD = 4            # 窗口两侧预留的晃动空间(像素),避免晃动时图像被裁边
SHAKE_SEQ = [0, -2, -4, -2]   # 对称晃动位移序列
CHAT_SENTENCES = [
    "大海深处很安静呢",
    "风…不对，是水流拂过发丝",
    "我在等一个笨蛋"
]
# -----------------------------------------------------------


def resource_path(name):
    """资源路径:兼容 PyInstaller 打包后运行与直接运行源码两种方式"""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


IMAGE_PATH = resource_path("pet.png")


class BubbleTip(QLabel):
    """半透明圆角对话气泡(独立小窗,自动跟随宠物,并限制在屏幕内)"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFont(QFont("Microsoft YaHei", 10))
        self.setStyleSheet("""
            QLabel{
                background-color:rgba(255,255,255,220);
                color:#40c4ff;
                padding:8px 12px;
                border-radius:12px;
            }
        """)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def _place(self, anchor):
        """anchor: 宠物窗口左上角坐标;气泡放在其上方,并限制在屏幕范围内"""
        screen = QApplication.primaryScreen().availableGeometry()
        x = anchor.x() + 10
        x = max(screen.left() + 8, min(x, screen.right() - self.width() - 8))
        y = anchor.y() - self.height() - 12
        y = max(screen.top() + 8, y)
        self.move(x, y)

    def show_text(self, text, anchor):
        self.setText(text)
        self.adjustSize()
        self._place(anchor)
        self.show()
        self.raise_()
        self.timer.start(BUBBLE_DURATION)

    def follow(self, anchor):
        """宠物移动 / 缩放 / 跳跃时,让气泡保持跟随(不重置显示计时)"""
        if self.isVisible():
            self._place(anchor)


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        self.scale = INIT_SCALE
        self.press_pos = QPoint()      # 按下左键时的全局坐标
        self.drag_offset = QPoint()    # 按下点相对窗口左上角的偏移
        self.is_dragging = False
        self.is_jumping = False
        self.is_on_top = True

        self.shake_timer = QTimer(self)
        self.shake_timer.timeout.connect(self.shake_effect)
        self.shake_index = 0

        # 加载图片(路径兼容打包 / 源码两种运行方式)
        self.raw_pix = QPixmap(IMAGE_PATH)
        if self.raw_pix.isNull():
            QMessageBox.critical(None, "桌宠", "找不到图片文件:\n" + IMAGE_PATH)
            sys.exit(1)
        self.original_w = self.raw_pix.width()
        self.original_h = self.raw_pix.height()

        # 窗口:无边框 + 透明 + 置顶;宽度两侧各留 SHAKE_PAD 供晃动
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(int(self.original_w * self.scale) + SHAKE_PAD * 2,
                    int(self.original_h * self.scale))

        self.label_img = QLabel(self)
        self.label_img.setAlignment(Qt.AlignCenter)
        self.update_pet_pixmap()

        self.bubble = BubbleTip()

        # 跳跃动画
        self.jump_anim = QPropertyAnimation(self, b"pos")
        self.jump_anim.setDuration(JUMP_DURATION)
        self.jump_anim.setEasingCurve(QEasingCurve.OutElastic)
        self.jump_anim.finished.connect(lambda: setattr(self, "is_jumping", False))
        self.jump_anim.valueChanged.connect(self.bubble.follow)

        self.move_to_init_pos()

    def move_to_init_pos(self):
        """初始位置:主屏幕右下角"""
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 40
        y = screen.bottom() - self.height() - 60
        self.move(max(screen.left(), x), max(screen.top(), y))

    def update_pet_pixmap(self):
        w = int(self.original_w * self.scale)
        h = int(self.original_h * self.scale)
        scaled = self.raw_pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label_img.setPixmap(scaled)
        self.label_img.resize(w, h)
        self.label_img.move(SHAKE_PAD, 0)
        self.resize(w + SHAKE_PAD * 2, h)
        self.keep_on_screen()

    def keep_on_screen(self):
        """缩放 / 移动后保证窗口不跑出屏幕"""
        screen = QApplication.primaryScreen().availableGeometry()
        x = min(self.x(), screen.right() - self.width())
        y = min(self.y(), screen.bottom() - self.height())
        self.move(max(screen.left(), x), max(screen.top(), y))

    def shake_effect(self):
        """拖动时的晃动效果(对称序列,图像不会超出窗口被裁掉)"""
        self.shake_index = (self.shake_index + 1) % len(SHAKE_SEQ)
        self.label_img.move(SHAKE_PAD + SHAKE_SEQ[self.shake_index], 0)

    # ---------- 鼠标事件 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.press_pos = event.globalPos()
            self.drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            self.is_dragging = False
        elif event.button() == Qt.RightButton:
            self.show_right_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if self.is_jumping:
            return
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.is_dragging:
            # 位移超过系统拖拽阈值才算拖动,避免单击时手抖被误判成拖动
            dist = (event.globalPos() - self.press_pos).manhattanLength()
            if dist < QApplication.startDragDistance():
                return
            self.is_dragging = True
        self.move(event.globalPos() - self.drag_offset)
        self.bubble.follow(self.pos())
        if not self.shake_timer.isActive():
            self.shake_timer.start(60)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.shake_timer.stop()
            self.shake_index = 0
            self.label_img.move(SHAKE_PAD, 0)
            if not self.is_dragging:
                # 单击:跳跃 + 气泡(跳跃进行中再点,只冒气泡不叠加跳跃)
                self.show_random_bubble()
                if not self.is_jumping:
                    self.play_jump_animation()
            self.is_dragging = False

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        step = 0.06
        if delta > 0:
            self.scale += step
        else:
            self.scale -= step
        self.scale = max(MIN_SCALE, min(MAX_SCALE, self.scale))
        self.update_pet_pixmap()
        self.bubble.follow(self.pos())

    # ---------- 动作 ----------
    def play_jump_animation(self):
        self.is_jumping = True
        start_pos = self.pos()
        up_y = start_pos.y() - 70
        self.jump_anim.setStartValue(start_pos)
        self.jump_anim.setKeyValueAt(0.4, QPoint(start_pos.x(), up_y))
        self.jump_anim.setEndValue(start_pos)
        self.jump_anim.start()

    def show_random_bubble(self):
        text = random.choice(CHAT_SENTENCES)
        self.bubble.show_text(text, self.pos())

    def show_right_menu(self, global_point):
        menu = QMenu()
        act_chat = menu.addAction("交互")
        act_big = menu.addAction("增加层数")
        act_small = menu.addAction("减少层数")
        act_reset = menu.addAction("零核比目鱼")
        act_toggle_top = menu.addAction("切换置顶")
        act_exit = menu.addAction("退出程序")

        action = menu.exec_(global_point)
        if action == act_chat:
            self.show_random_bubble()
        elif action == act_big:
            self.scale = min(self.scale + 0.12, MAX_SCALE)
            self.update_pet_pixmap()
        elif action == act_small:
            self.scale = max(self.scale - 0.12, MIN_SCALE)
            self.update_pet_pixmap()
        elif action == act_reset:
            self.scale = INIT_SCALE
            self.update_pet_pixmap()
        elif action == act_toggle_top:
            self.toggle_stay_top()
        elif action == act_exit:
            QApplication.quit()

    def toggle_stay_top(self):
        self.is_on_top = not self.is_on_top
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.is_on_top)
        self.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())
