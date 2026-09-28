import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { clone } from 'three/addons/utils/SkeletonUtils.js';

const $ = (selector, parent = document) => parent.querySelector(selector);
const loader = new GLTFLoader();
const sourceCache = new Map();
const skillNames = {
  'character-body-mechanics': '身体力学',
  'character-prop-interaction': '物体交互',
  'character-acting': '身体表演',
};
const shortNames = {
  'walk-turn-stop': '行走、转向与停稳', 'sit-stand': '坐下与起立',
  'low-seat-transfer': '低凳起身并迈步', 'lift-heavy-box': '双手搬起重箱',
  'axe-strike': '双手持斧劈木', 'wide-crate-transfer': '抱宽箱转身放下',
  'alert-turn': '警觉转身', 'tired-walk': '疲惫行走与喘息',
  'relief-transfer': '确认安全后放松',
};
const order = Object.keys(shortNames);
let cases = [], currentCase, time = 0, duration = 0, playing = false, previousFrame = 0;
let comparing = false, cameraMode = 'perspective';
const views = [];
const hasFiles = event => Array.from(event.dataTransfer?.types || []).includes('Files');

// Keep files dropped outside a viewport from replacing the page.
for (const type of ['dragover', 'drop']) document.addEventListener(type, event => {
  if (!hasFiles(event)) return;
  event.preventDefault();
  if (!event.target.closest('.viewport')) event.dataTransfer.dropEffect = 'none';
});

function option(value, label) {
  const node = document.createElement('option');
  node.value = value;
  node.textContent = label;
  return node;
}

function dispose(group) {
  const textures = new Set();
  group.traverse(node => {
    node.geometry?.dispose();
    for (const material of [node.material].flat().filter(Boolean)) {
      for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
      material.dispose();
    }
  });
  textures.forEach(texture => texture.dispose());
}

class Viewport {
  constructor(element) {
    this.element = element;
    this.epoch = 0;
    this.duration = 0;
    this.kind = 'source';
    this.status = $('.canvas-status', element);
    this.modelSelect = $('.model-select', element);
    this.clipSelect = $('.clip-select', element);
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xe8e9e1);
    this.camera = new THREE.PerspectiveCamera(36, 1, 0.03, 150);
    this.renderer = new THREE.WebGLRenderer({ canvas: $('canvas', element), antialias: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.25;
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.minDistance = 0.5;
    this.controls.maxDistance = 20;
    this.controls.maxPolarAngle = Math.PI * 0.49;
    this.scene.add(new THREE.HemisphereLight(0xf8f9ed, 0x8e9682, 2.5));
    const key = new THREE.DirectionalLight(0xfff5df, 3.2);
    key.position.set(-3, 7, -4);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.camera.left = key.shadow.camera.bottom = -5;
    key.shadow.camera.right = key.shadow.camera.top = 5;
    key.shadow.normalBias = 0.02;
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0xe3edff, 1.7);
    fill.position.set(4, 3, 2);
    this.scene.add(fill);
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(100, 100),
      new THREE.MeshStandardMaterial({ color: 0xdfe3d6, roughness: 1 }));
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.012;
    ground.receiveShadow = true;
    this.scene.add(ground);
    const grid = new THREE.GridHelper(14, 28, 0xb1bbaa, 0xcbd1c3);
    grid.material.transparent = true;
    grid.material.opacity = 0.55;
    this.scene.add(grid);
    this.context = new THREE.Group();
    this.scene.add(this.context);
    this.setCamera('perspective');
    new ResizeObserver(() => {
      const bounds = $('.canvas-wrap', element).getBoundingClientRect();
      if (!bounds.width || !bounds.height) return;
      this.renderer.setSize(bounds.width, bounds.height, false);
      this.camera.aspect = bounds.width / bounds.height;
      this.camera.updateProjectionMatrix();
    }).observe($('.canvas-wrap', element));
    this.modelSelect.addEventListener('change', () => this.loadChoice());
    this.clipSelect.addEventListener('change', () => this.selectClip(this.clipSelect.value));
    $('.file-input', element).addEventListener('change', event => {
      const file = event.target.files[0];
      event.target.value = '';
      if (file) this.loadFile(file);
    });
    let dragDepth = 0;
    element.addEventListener('dragenter', event => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      dragDepth += 1;
      element.classList.add('drag-over');
    });
    element.addEventListener('dragover', event => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'copy';
    });
    element.addEventListener('dragleave', event => {
      if (!hasFiles(event)) return;
      dragDepth = Math.max(0, dragDepth - 1);
      if (!dragDepth) element.classList.remove('drag-over');
    });
    element.addEventListener('drop', event => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      dragDepth = 0;
      element.classList.remove('drag-over');
      if (event.dataTransfer.files.length !== 1) {
        this.beginLoad();
        this.fail('每个视图一次载入一个 GLB 文件，请重新拖入。');
        return;
      }
      this.loadFile(event.dataTransfer.files[0]);
    });
  }

  async loadFile(file) {
    const epoch = this.beginLoad();
    if (!file.name.toLowerCase().endsWith('.glb')) {
      this.fail('仅支持 GLB 文件，请重新拖入或选择 .glb 文件。');
      return;
    }
    try {
      const gltf = await loader.parseAsync(await file.arrayBuffer(), '');
      if (epoch !== this.epoch) { dispose(gltf.scene); return; }
      this.modelSelect.querySelector('[value="local"]')?.remove();
      this.modelSelect.append(option('local', file.name));
      this.modelSelect.value = 'local';
      this.showModel(gltf, { kind: 'local', label: file.name, verdict: 'pending' }, true);
    } catch (error) {
      if (epoch === this.epoch) this.fail('GLB 无法读取，请重新拖入或选择有效文件。');
      console.error(error);
    }
  }

  beginLoad() {
    this.epoch += 1;
    this.status.hidden = false;
    this.status.classList.remove('error');
    this.status.textContent = '正在加载模型……';
    this.element.dataset.state = 'loading';
    this.clearModel();
    this.clipSelect.disabled = true;
    this.clipSelect.replaceChildren(option('', '绑定姿势'));
    $('.clip-duration', this.element).textContent = '';
    updatePlayback();
    return this.epoch;
  }

  clearModel() {
    this.mixer?.stopAllAction();
    if (this.model) {
      this.scene.remove(this.model);
      if (this.ownsModel) dispose(this.model);
    }
    if (this.skeleton) {
      this.scene.remove(this.skeleton);
      this.skeleton.dispose();
    }
    this.model = this.skeleton = this.mixer = this.action = null;
    this.duration = 0;
  }

  fail(message) {
    this.status.textContent = message;
    this.status.classList.add('error');
    this.status.hidden = false;
    this.element.dataset.state = 'error';
    updatePlayback();
  }

  async setCase(task) {
    this.task = task;
    this.modelSelect.replaceChildren(...task.models.map(model => option(model.id, model.label)));
    const available = task.models.filter(model => model.available && model.kind !== 'source');
    const recorded = [...available].reverse().find(model => model.kind === 'corrected') || available.at(-1);
    this.modelSelect.value = recorded?.id || task.models[0]?.id || '';
    this.createContext(task);
    await this.loadChoice();
  }

  async loadChoice() {
    const choice = this.task.models.find(model => model.id === this.modelSelect.value);
    if (!choice) return;
    const epoch = this.beginLoad();
    if (!choice.available) {
      this.fail('素材缺失或校验不一致。恢复原始文件后刷新，或载入本地 GLB。');
      return;
    }
    try {
      let gltf;
      if (choice.kind === 'source') {
        if (!sourceCache.has(choice.url)) {
          sourceCache.set(choice.url, loader.loadAsync(choice.url).catch(error => {
            sourceCache.delete(choice.url);
            throw error;
          }));
        }
        const original = await sourceCache.get(choice.url);
        gltf = { scene: clone(original.scene), animations: original.animations };
      } else {
        gltf = await loader.loadAsync(choice.url);
      }
      if (epoch !== this.epoch) {
        if (choice.kind !== 'source') dispose(gltf.scene);
        return;
      }
      this.showModel(gltf, choice, choice.kind !== 'source');
    } catch (error) {
      if (epoch === this.epoch) this.fail('模型加载失败。检查素材后刷新，或载入本地 GLB。');
      console.error(error);
    }
  }

  showModel(gltf, choice, ownsModel) {
    this.kind = choice.kind;
    this.ownsModel = ownsModel;
    this.model = new THREE.Group();
    this.model.add(gltf.scene);
    this.scene.add(this.model);
    // Normalize only fixed inputs. Production exports retain their authored units and root motion.
    if (choice.kind === 'source') {
      this.model.rotation.y = Math.PI;
      this.model.updateMatrixWorld(true);
      let box = new THREE.Box3().setFromObject(this.model);
      const height = box.getSize(new THREE.Vector3()).y;
      this.model.scale.setScalar(this.task.scene.character_height / Math.max(height, 0.01));
      this.model.updateMatrixWorld(true);
      box = new THREE.Box3().setFromObject(this.model);
      const center = box.getCenter(new THREE.Vector3());
      this.model.position.set(-center.x, -box.min.y, -center.z);
    }
    this.model.traverse(node => {
      if (node.isMesh) {
        node.castShadow = true;
        node.receiveShadow = true;
        node.frustumCulled = false;
      }
    });
    this.model.updateMatrixWorld(true);
    this.skeleton = new THREE.SkeletonHelper(gltf.scene);
    this.skeleton.material.depthTest = false;
    this.skeleton.material.transparent = true;
    this.skeleton.material.opacity = 0.8;
    this.skeleton.visible = $('#skeleton').checked;
    this.scene.add(this.skeleton);
    this.clips = gltf.animations;
    this.mixer = new THREE.AnimationMixer(gltf.scene);
    this.clipSelect.replaceChildren(option('', '绑定姿势'),
      ...this.clips.map((clip, index) => option(String(index), clip.name || `动作 ${index + 1}`)));
    this.clipSelect.disabled = false;
    const preferred = choice.kind === 'source'
      ? this.clips.findIndex(clip => clip.name === (this.task.id === 'walk-turn-stop' ? 'Walk' : 'Idle')) : 0;
    this.clipSelect.value = this.clips.length ? String(Math.max(0, preferred)) : '';
    this.selectClip(this.clipSelect.value);
    const labels = { source: '源素材 · 非案例产物', local: '本地 GLB · 未登记评价', initial: '初稿', corrected: '修正版' };
    const verdicts = { pending: '待评价', accepted: '记录已接受', rejected: '记录未通过' };
    $('.view-origin', this.element).textContent = labels[choice.kind] +
      (['initial', 'corrected'].includes(choice.kind) ? ` · ${verdicts[choice.verdict]}` : '');
    this.context.visible = choice.kind === 'source' && $('#props').checked;
    this.status.hidden = true;
    this.element.dataset.state = 'ready';
    this.element.dataset.kind = choice.kind;
    this.setCamera(cameraMode);
    updatePlayback();
  }

  selectClip(value) {
    this.mixer?.stopAllAction();
    this.action = null;
    this.duration = 0;
    if (value !== '' && this.clips[Number(value)]) {
      const clip = this.clips[Number(value)];
      this.duration = clip.duration;
      this.action = this.mixer.clipAction(clip);
      this.action.setLoop(THREE.LoopOnce);
      this.action.clampWhenFinished = true;
      this.action.reset().play();
    }
    $('.clip-duration', this.element).textContent = this.duration ? `${this.duration.toFixed(2)} s` : '静态姿势';
    time = 0;
    updatePlayback();
  }

  setCamera(mode) {
    const id = this.task?.id;
    const targets = {
      'walk-turn-stop': [0.45, 0.95, -1.05], 'tired-walk': [0, 0.95, -1],
      'wide-crate-transfer': [-0.4, 0.85, -0.15], 'lift-heavy-box': [0.4, 0.95, -0.2],
      'axe-strike': [0, 1.1, -0.35],
    };
    const target = new THREE.Vector3(...(targets[id] || [0, 0.95, 0]));
    const positions = { perspective: [3.0, 1.55, -4.1], front: [0, 0.05, -5.2], side: [5.8, 0.05, 0],
      grip: [2.1, 0.9, -2.7], impact: [1.8, 0.65, -1.8] };
    if (mode === 'grip') target.set(id === 'wide-crate-transfer' ? -0.4 : 0.45, 0.8, -0.35);
    if (mode === 'impact') target.set(0, 0.65, -0.85);
    const offset = new THREE.Vector3(...positions[mode]);
    if (id === 'wide-crate-transfer' && ['perspective', 'grip'].includes(mode)) offset.x *= -1;
    this.controls.target.copy(target);
    this.camera.position.copy(target).add(offset);
    this.controls.update();
  }

  createContext(task) {
    dispose(this.context);
    this.context.clear();
    const material = new THREE.MeshStandardMaterial({ color: 0xa28f6d, roughness: 0.95 });
    const position = (x, y, z) => new THREE.Vector3(x, z, -y);
    const box = (dimensions, center, color) => {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(dimensions[0], dimensions[2], dimensions[1]),
        color ? new THREE.MeshStandardMaterial({ color, roughness: 0.95 }) : material);
      mesh.position.copy(position(...center));
      mesh.castShadow = mesh.receiveShadow = true;
      this.context.add(mesh);
      return mesh;
    };
    for (const prop of task.scene.props || []) {
      if (prop.dimensions) {
        box(prop.dimensions, prop.center, 0xa39576);
      } else if (prop.seat_dimensions || prop.top_dimensions) {
        const dimensions = prop.seat_dimensions || prop.top_dimensions;
        const top = prop.seat_top_z ?? prop.top_z;
        const xy = prop.seat_center_xy || prop.center_xy;
        box(dimensions, [...xy, top - dimensions[2] / 2]);
        for (const x of [-1, 1]) for (const y of [-1, 1]) {
          box([0.06, 0.06, top - dimensions[2]],
            [xy[0] + x * (dimensions[0] / 2 - 0.05), xy[1] + y * (dimensions[1] / 2 - 0.05),
              (top - dimensions[2]) / 2], 0x827659);
        }
      } else if (prop.radius) {
        const stump = new THREE.Mesh(new THREE.CylinderGeometry(prop.radius, prop.radius * 1.05, prop.top_z, 24), material);
        stump.position.copy(position(...prop.center_xy, prop.top_z / 2));
        stump.castShadow = stump.receiveShadow = true;
        this.context.add(stump);
      }
    }
    if (task.id === 'walk-turn-stop' || task.id === 'tired-walk') {
      const points = [new THREE.Vector3(0, 0.012, 0), new THREE.Vector3(0, 0.012, -2)];
      if (task.id === 'walk-turn-stop') points.push(new THREE.Vector3(1, 0.012, -2));
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),
        new THREE.LineDashedMaterial({ color: 0x899b75, dashSize: 0.1, gapSize: 0.07 }));
      line.computeLineDistances();
      this.context.add(line);
    }
  }

  render(cursor) {
    if (this.action) {
      this.action.enabled = true;
      this.action.paused = false;
      this.mixer.setTime(Math.min(cursor, this.duration));
    }
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}

function activeViews() { return comparing ? views : views.slice(0, 1); }

function setPlaying(value) {
  playing = value && duration > 0;
  if (playing) previousFrame = performance.now();
  $('#play').classList.toggle('playing', playing);
  $('#play').setAttribute('aria-label', playing ? '暂停' : '播放');
}

function updatePlayback() {
  duration = Math.max(0, ...activeViews().map(view => view.duration));
  time = Math.min(time, duration);
  for (const id of ['play', 'step', 'timeline']) $(`#${id}`).disabled = !duration;
  $('#timeline').max = String(duration || 1);
  if (!duration) setPlaying(false);
  const hasSource = activeViews().some(view => view.kind === 'source');
  $('#source-note').textContent = hasSource
    ? '源素材自带动作仅供预览，不是当前案例的制作结果。任务布景按 case 尺寸展示。'
    : '播放所选 GLB；双视图按秒同步，较短片段停在末帧。评价状态取自运行记录。';
}

function renderList() {
  const query = $('#search').value.trim().toLowerCase();
  const container = $('#case-list');
  container.replaceChildren();
  for (const [skill, label] of Object.entries(skillNames)) {
    const matches = cases.filter(task => task.skill === skill &&
      `${task.title} ${task.id} ${label}`.toLowerCase().includes(query));
    if (!matches.length) continue;
    const group = document.createElement('div');
    group.className = 'case-group';
    const title = document.createElement('p');
    title.className = 'group-name';
    title.textContent = label;
    group.append(title);
    for (const task of matches) {
      const button = document.createElement('button');
      button.className = `case-button${currentCase?.id === task.id ? ' active' : ''}`;
      button.dataset.case = task.id;
      button.setAttribute('aria-current', currentCase?.id === task.id ? 'true' : 'false');
      const number = document.createElement('span');
      number.className = 'case-number';
      number.textContent = String(cases.indexOf(task) + 1).padStart(2, '0');
      const copy = document.createElement('span');
      copy.className = 'case-copy';
      const name = document.createElement('span');
      name.className = 'case-name';
      name.textContent = shortNames[task.id] || task.title;
      const note = document.createElement('span');
      note.className = 'case-subline';
      note.textContent = `${task.split === 'transfer' ? '迁移' : '开发'} · ${task.duration_seconds} 秒 · ${task.run_count ? `${task.run_count} 次记录` : '待制作'}`;
      copy.append(name, note);
      button.append(number, copy);
      button.addEventListener('click', () => selectCase(task));
      group.append(button);
    }
    container.append(group);
  }
  if (!container.children.length) {
    const empty = document.createElement('p');
    empty.className = 'muted';
    empty.textContent = '未找到相关案例';
    container.append(empty);
  }
}

async function selectCase(task) {
  currentCase = task;
  setPlaying(false);
  time = 0;
  $('#case-title').textContent = shortNames[task.id] || task.title;
  $('#skill-name').textContent = skillNames[task.skill] || task.skill;
  $('#case-split').textContent = task.split === 'transfer' ? '迁移案例' : '开发案例';
  $('#case-spec').textContent = `${task.duration_seconds} 秒任务 · ${task.fps} fps · ${task.scene.character_height} m 角色`;
  $('#production-status').textContent = task.run_count ? `${task.run_count} 次制作记录` : '待制作';
  $('#task-prompt').textContent = task.prompt;
  for (const group of ['correctness', 'taste']) {
    $(`#${group}`).replaceChildren(...task.criteria[group].map(criterion => {
      const item = document.createElement('li');
      item.textContent = criterion.description;
      return item;
    }));
  }
  history.replaceState(null, '', `#${task.id}`);
  renderList();
  // Both panes share the source cache but have independent skeletons and mixers.
  await Promise.all(views.map(view => view.setCase(task)));
  if (currentCase === task) updatePlayback();
}

function frame(timestamp) {
  const delta = previousFrame ? (timestamp - previousFrame) / 1000 : 0;
  previousFrame = timestamp;
  if (playing && duration) {
    time += delta * Number($('#speed').value);
    if (time >= duration) {
      if ($('#loop').checked) time %= duration;
      else { time = duration; setPlaying(false); }
    }
  }
  $('#timeline').value = String(time);
  $('#time').value = `${time.toFixed(2)} / ${duration.toFixed(2)} s`;
  activeViews().forEach(view => view.render(time));
  requestAnimationFrame(frame);
}

async function start() {
  try {
    const response = await fetch('/api/cases');
    if (!response.ok) throw new Error('案例数据无法读取，请检查工程记录后刷新页面。');
    const data = await response.json();
    cases = data.cases.sort((a, b) => {
      const ai = order.indexOf(a.id), bi = order.indexOf(b.id);
      return (ai < 0 ? Infinity : ai) - (bi < 0 ? Infinity : bi);
    });
    $('#case-count').textContent = `${cases.length} 项`;
    if (!cases.length) throw new Error('暂无案例。在 cases 目录添加任务后刷新页面。');
    views.push(new Viewport($('#viewport-a')), new Viewport($('#viewport-b')));
    $('#search').addEventListener('input', renderList);
    $('#play').addEventListener('click', () => {
      if (time >= duration) time = 0;
      setPlaying(!playing);
    });
    $('#step').addEventListener('click', () => {
      setPlaying(false);
      time = Math.min(duration, time + 1 / currentCase.fps);
    });
    $('#timeline').addEventListener('input', event => { setPlaying(false); time = Number(event.target.value); });
    $('#compare').addEventListener('click', () => {
      comparing = !comparing;
      $('#viewports').classList.toggle('compare', comparing);
      $('#viewport-b').hidden = !comparing;
      $('#compare').setAttribute('aria-pressed', String(comparing));
      updatePlayback();
    });
    $('#skeleton').addEventListener('change', event => views.forEach(view => {
      if (view.skeleton) view.skeleton.visible = event.target.checked;
    }));
    $('#props').addEventListener('change', event => views.forEach(view => {
      view.context.visible = event.target.checked && view.kind === 'source';
    }));
    document.querySelectorAll('[data-camera]').forEach(button => button.addEventListener('click', () => {
      cameraMode = button.dataset.camera;
      views.forEach(view => view.setCamera(cameraMode));
      document.querySelectorAll('[data-camera]').forEach(item => {
        item.classList.toggle('selected', item === button);
        item.setAttribute('aria-pressed', String(item === button));
      });
    }));
    document.addEventListener('keydown', event => {
      if (event.code !== 'Space' || /^(INPUT|SELECT|TEXTAREA|BUTTON|SUMMARY)$/.test(event.target.tagName)) return;
      event.preventDefault();
      if (time >= duration) time = 0;
      setPlaying(!playing);
    });
    document.addEventListener('visibilitychange', () => {
      previousFrame = 0;
      if (document.hidden) setPlaying(false);
    });
    requestAnimationFrame(frame);
    await selectCase(cases.find(task => task.id === location.hash.slice(1)) || cases[0]);
  } catch (error) {
    $('#app-error').textContent = error.message.includes('WebGL')
      ? '无法启动 3D 预览，请使用支持 WebGL 2 的浏览器并启用硬件加速。'
      : '查看器加载失败。检查本地服务、案例数据和浏览器控制台后刷新页面。';
    $('#app-error').hidden = false;
    console.error(error);
  }
}

start();
