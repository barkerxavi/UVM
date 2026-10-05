"""Asynchronous OpenGL preview for polygon meshes in a USD stage."""

import math

import numpy as np
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QMatrix4x4, QPainter, QQuaternion, QVector3D
from PySide6.QtOpenGL import (
    QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram,
    QOpenGLVertexArrayObject,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget


def build_mesh_buffer(path, preferred_purpose="proxy"):
    """Read and triangulate USD meshes off the UI thread."""
    try:
        from pxr import Usd, UsdGeom
    except ImportError as exc:
        raise RuntimeError("USD Python bindings are required to load a stage.") from exc

    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise RuntimeError(f"Could not open USD stage: {path}")

    xform_cache = UsdGeom.XformCache()
    unscoped_meshes = []
    representation_groups = {}
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        imageable = UsdGeom.Imageable(prim)
        if str(imageable.ComputeVisibility()) == "invisible":
            continue

        path_parts = [part.lower() for part in str(prim.GetPath()).split("/")]
        purpose = str(imageable.ComputePurpose())
        category_index = next(
            (i for i, part in enumerate(path_parts) if part in ("render", "proxy", "guide")),
            None,
        )
        if category_index is not None:
            display_group = path_parts[category_index]
            family = "/" + "/".join(path_parts[1:category_index])
        else:
            display_group = purpose if purpose in ("render", "proxy", "guide") else "default"
            family = (
                str(prim.GetPath().GetParentPath())
                if display_group != "default" else None
            )

        mesh = UsdGeom.Mesh(prim)
        points = mesh.GetPointsAttr().Get()
        counts = mesh.GetFaceVertexCountsAttr().Get()
        indices = mesh.GetFaceVertexIndicesAttr().Get()
        if points is None or counts is None or indices is None or len(points) == 0:
            continue

        # A Gf matrix uses row vectors, so points multiplied by the matrix
        # receive the same local-to-world transform as Gf.Matrix4d.Transform.
        point_array = np.asarray(points, dtype=np.float64)
        matrix = np.asarray(xform_cache.GetLocalToWorldTransform(prim), dtype=np.float64)
        homogeneous = np.concatenate(
            (point_array, np.ones((len(point_array), 1), dtype=np.float64)), axis=1
        )
        world_points = (homogeneous @ matrix)[:, :3]

        mesh_face_triangles = []
        mesh_face_normals = []
        offset = 0
        face_number = 0
        normal_values = mesh.GetNormalsAttr().Get()
        normal_interpolation = str(mesh.GetNormalsInterpolation())
        expected_normal_counts = {
            "constant": 1,
            "uniform": len(counts),
            "vertex": len(points),
            "varying": len(points),
            "faceVarying": sum(int(value) for value in counts),
        }
        has_authored_normals = (
            normal_values is not None
            and normal_interpolation in expected_normal_counts
            and len(normal_values) == expected_normal_counts[normal_interpolation]
        )
        if has_authored_normals:
            normal_array = np.asarray(normal_values, dtype=np.float64)
            normal_matrix = np.linalg.inv(matrix[:3, :3]).T
            normal_array = normal_array @ normal_matrix
            normal_lengths = np.linalg.norm(normal_array, axis=1)
            valid_normals = np.isfinite(normal_array).all(axis=1) & (normal_lengths > 1e-10)
            normal_array[valid_normals] /= normal_lengths[valid_normals, None]
            normal_array[~valid_normals] = 0.0

        for count_value in counts:
            count = int(count_value)
            if count >= 3:
                face = indices[offset:offset + count]
                # Fan triangulation for the convex polygon faces common in USD.
                fan_count = count - 2
                local_triangles = np.column_stack((
                    np.zeros(fan_count, dtype=np.intp),
                    np.arange(1, count - 1, dtype=np.intp),
                    np.arange(2, count, dtype=np.intp),
                ))
                mesh_face_triangles.append(np.asarray(face, dtype=np.intp)[local_triangles])
                if has_authored_normals:
                    if normal_interpolation in ("vertex", "varying"):
                        normal_indices = np.asarray(face, dtype=np.intp)[local_triangles]
                    elif normal_interpolation == "faceVarying":
                        normal_indices = offset + local_triangles
                    elif normal_interpolation == "uniform":
                        normal_indices = np.full((fan_count, 3), face_number, dtype=np.intp)
                    else:  # constant
                        normal_indices = np.zeros((fan_count, 3), dtype=np.intp)
                    mesh_face_normals.append(normal_array[normal_indices])
            offset += count
            face_number += 1
        if mesh_face_triangles:
            triangle_indices = np.concatenate(mesh_face_triangles, axis=0)
            triangle_positions = world_points[triangle_indices]
            if has_authored_normals and mesh_face_normals:
                triangle_normals = np.concatenate(mesh_face_normals, axis=0)
                flat_normals = np.cross(
                    triangle_positions[:, 1] - triangle_positions[:, 0],
                    triangle_positions[:, 2] - triangle_positions[:, 0],
                )
                lengths = np.linalg.norm(flat_normals, axis=1)
                valid_faces = np.isfinite(flat_normals).all(axis=1) & (lengths > 1e-10)
                flat_normals[valid_faces] /= lengths[valid_faces, None]
                flat_normals[~valid_faces] = (0.0, 0.0, 1.0)
                invalid = ~np.isfinite(triangle_normals).all(axis=2)
                invalid |= np.linalg.norm(triangle_normals, axis=2) <= 1e-10
                flat_per_vertex = np.repeat(flat_normals[:, None, :], 3, axis=1)
                triangle_normals[invalid] = flat_per_vertex[invalid]
            else:
                flat_normals = np.cross(
                    triangle_positions[:, 1] - triangle_positions[:, 0],
                    triangle_positions[:, 2] - triangle_positions[:, 0],
                )
                lengths = np.linalg.norm(flat_normals, axis=1)
                lengths[lengths == 0] = 1.0
                flat_normals /= lengths[:, None]
                triangle_normals = np.repeat(flat_normals[:, None, :], 3, axis=1)
            mesh_data = (triangle_positions, triangle_normals)
            if family is None:
                unscoped_meshes.append(mesh_data)
            else:
                representation_groups.setdefault(family, {}).setdefault(display_group, []).append(mesh_data)

    # Purpose branches are alternate representations of one model. Choose one
    # per branch, while keeping independent models elsewhere in the stage.
    mesh_triangles = list(unscoped_meshes)
    preference_order = (
        ("proxy", "default", "render", "guide")
        if preferred_purpose == "proxy"
        else ("render", "default", "proxy", "guide")
    )
    for representations in representation_groups.values():
        for purpose in preference_order:
            if representations.get(purpose):
                mesh_triangles.extend(representations[purpose])
                break

    if not mesh_triangles:
        raise RuntimeError("This stage contains no renderable polygon mesh faces.")

    triangles = np.concatenate([mesh[0] for mesh in mesh_triangles], axis=0)
    normals = np.concatenate([mesh[1] for mesh in mesh_triangles], axis=0)
    bounds_min = triangles.min(axis=(0, 1))
    bounds_max = triangles.max(axis=(0, 1))
    center = (bounds_min + bounds_max) * 0.5
    radius = max(float(np.linalg.norm(bounds_max - bounds_min) * 0.5), 1e-4)
    positions = ((triangles - center) * (0.9 / radius)).astype(np.float32)

    vertices = np.concatenate((positions, normals.astype(np.float32)), axis=2).reshape(-1, 6)
    return vertices.tobytes(), len(vertices)


class MeshLoadThread(QThread):
    loaded = Signal(bytes, int)
    failed = Signal(str)

    def __init__(self, path, preferred_purpose="proxy", parent=None):
        super().__init__(parent)
        self.path = str(path)
        self.preferred_purpose = preferred_purpose

    def run(self):
        try:
            data, vertex_count = build_mesh_buffer(self.path, self.preferred_purpose)
            self.loaded.emit(data, vertex_count)
        except Exception as exc:
            self.failed.emit(str(exc))


class UsdMeshViewer(QOpenGLWidget):
    """Render triangulated UsdGeom.Mesh geometry with a headlight shader."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self._program = None
        self._buffer = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self._vao = QOpenGLVertexArrayObject()
        self._vertex_count = 0
        self._distance = 4.0
        self._rotation = QQuaternion()
        self._target = QVector3D(0.0, 0.0, 0.0)
        self._drag_mode = None
        self._mesh_data = b""
        self._message = "Loading USD meshes…"

    def set_mesh_data(self, data, vertex_count):
        self._mesh_data = data
        self._vertex_count = vertex_count
        self._distance = 4.0
        self._rotation = QQuaternion()
        self._target = QVector3D(0.0, 0.0, 0.0)
        self._message = ""
        if self.isValid():
            self.makeCurrent()
            self._upload_mesh()
            self.doneCurrent()
        self.update()

    def set_error(self, message):
        self._message = message
        self.update()

    def initializeGL(self):
        functions = self.context().functions()
        functions.glEnable(0x0B71)  # GL_DEPTH_TEST
        functions.glDisable(0x0B44)  # GL_CULL_FACE: show both face orientations
        program = QOpenGLShaderProgram(self)
        vertex_shader = """#version 150
            in vec3 position;
            in vec3 normal;
            uniform mat4 mvp;
            uniform mat3 normalMatrix;
            out vec3 surfaceNormal;
            void main() {
                gl_Position = mvp * vec4(position, 1.0);
                surfaceNormal = normalMatrix * normal;
            }
        """
        fragment_shader = """#version 150
            in vec3 surfaceNormal;
            out vec4 fragmentColor;
            void main() {
                vec3 n = normalize(surfaceNormal);
                float headlight = abs(dot(n, vec3(0.0, 0.0, 1.0)));
                float intensity = 0.24 + 0.76 * headlight;
                fragmentColor = vec4(vec3(0.72, 0.77, 0.84) * intensity, 1.0);
            }
        """
        if not program.addShaderFromSourceCode(QOpenGLShader.Vertex, vertex_shader):
            self._message = program.log()
            return
        if not program.addShaderFromSourceCode(QOpenGLShader.Fragment, fragment_shader):
            self._message = program.log()
            return
        program.bindAttributeLocation("position", 0)
        program.bindAttributeLocation("normal", 1)
        if not program.link():
            self._message = program.log()
            return
        self._program = program
        if not self._vao.create():
            self._message = "Could not create an OpenGL vertex array object."
            return
        self._buffer.create()
        self._upload_mesh()

    def _upload_mesh(self):
        if self._buffer.isCreated() and self._mesh_data:
            self._buffer.bind()
            self._buffer.allocate(self._mesh_data, len(self._mesh_data))
            self._buffer.release()

    def resizeGL(self, width, height):
        self.context().functions().glViewport(0, 0, width, height)

    def paintGL(self):
        functions = self.context().functions()
        functions.glEnable(0x0B71)  # GL_DEPTH_TEST
        functions.glDepthFunc(0x0201)  # GL_LESS
        functions.glDepthMask(True)
        functions.glDisable(0x0B44)  # GL_CULL_FACE
        functions.glClearColor(0.10, 0.11, 0.13, 1.0)
        functions.glClear(0x00004000 | 0x00000100)  # COLOR | DEPTH
        if self._message:
            painter = QPainter(self)
            painter.setPen(Qt.white)
            painter.drawText(self.rect(), Qt.AlignCenter | Qt.TextWordWrap, self._message)
            painter.end()
            return
        if self._program is None or not self._vertex_count:
            return
        if not self._vao.isCreated():
            self._message = "The OpenGL vertex array object is unavailable."
            self.update()
            return
        self._vao.bind()
        if not self._buffer.bind():
            self._vao.release()
            self._message = "Could not bind the OpenGL mesh buffer."
            self.update()
            return

        aspect = max(self.width() / max(self.height(), 1), 1e-3)
        projection = QMatrix4x4()
        projection.perspective(35.0, aspect, 0.01, 100.0)
        view = QMatrix4x4()
        view.lookAt(
            self._target + QVector3D(0.0, 0.0, self._distance),
            self._target,
            QVector3D(0.0, 1.0, 0.0),
        )
        model = QMatrix4x4()
        model.rotate(self._rotation)
        self._program.bind()
        self._program.setUniformValue("mvp", projection * view * model)
        self._program.setUniformValue("normalMatrix", model.normalMatrix())
        self._program.enableAttributeArray(0)
        self._program.setAttributeBuffer(0, 0x1406, 0, 3, 24)  # GL_FLOAT, stride 6 floats
        self._program.enableAttributeArray(1)
        self._program.setAttributeBuffer(1, 0x1406, 12, 3, 24)  # normal starts after position
        functions.glDrawArrays(0x0004, 0, self._vertex_count)  # GL_TRIANGLES
        self._program.disableAttributeArray(0)
        self._program.disableAttributeArray(1)
        self._program.release()
        self._buffer.release()
        self._vao.release()

    def wheelEvent(self, event):
        pixel_delta = event.pixelDelta().y()
        if pixel_delta:
            zoom_delta = pixel_delta / 120.0
        else:
            zoom_delta = event.angleDelta().y() / 120.0
        factor = math.exp(-zoom_delta * 0.18)
        self._distance = max(0.25, min(40.0, self._distance * factor))
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        self._last_mouse_pos = event.position().toPoint()
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and event.modifiers() & Qt.ShiftModifier
        ):
            self._drag_mode = "pan"
        elif event.button() == Qt.LeftButton:
            self._drag_mode = "orbit"
        event.accept()

    def mouseMoveEvent(self, event):
        current = event.position().toPoint()
        delta = current - self._last_mouse_pos
        self._last_mouse_pos = current
        if self._drag_mode == "pan":
            world_per_pixel = (
                2.0 * self._distance * math.tan(math.radians(35.0 * 0.5))
                / max(self.height(), 1)
            )
            self._target.setX(self._target.x() - delta.x() * world_per_pixel)
            self._target.setY(self._target.y() + delta.y() * world_per_pixel)
        elif self._drag_mode == "orbit":
            yaw = QQuaternion.fromAxisAndAngle(QVector3D(0.0, 1.0, 0.0), delta.x() * 0.6)
            pitch = QQuaternion.fromAxisAndAngle(QVector3D(1.0, 0.0, 0.0), delta.y() * 0.6)
            self._rotation = yaw * pitch * self._rotation
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_mode = None
        event.accept()
