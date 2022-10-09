function define(object, properties) {
  for (const name of Object.getOwnPropertyNames(properties)) {
    const propDesc = Object.getOwnPropertyDescriptor(properties, name);
    Object.defineProperty(object, name, propDesc);
  }
};

class Screen {
  get availWidth() { return 1920; }
  get availHeight() { return 1022; }
  get width() { return 1920; }
  get height() { return 1080; }
  get colorDepth() { return 24; }
  get pixelDepth() { return 24; }
}
Object.defineProperties(Screen.prototype, {
  availWidth: { enumerable: true },
  availHeight: { enumerable: true },
  width: { enumerable: true },
  height: { enumerable: true },
  colorDepth: { enumerable: true },
  pixelDepth: { enumerable: true },
  [Symbol.toStringTag]: { value: "Screen", configurable: true }
});

class Storage {
  constructor() {
    this.st = {}
  }

  key(index) {
    if (arguments.length < 1) {
      throw new TypeError("Failed to execute 'key' on 'Storage': 1 argument required, but only " + arguments.length + " present.");
    }
    const args = [];
    { let curArg = arguments[0]; args.push(curArg);}
    return this.st.key(...args);
  }

  getItem(key) {
    if (arguments.length < 1) {
      throw new TypeError("Failed to execute 'getItem' on 'Storage': 1 argument required, but only " + arguments.length + " present.");
    }
    const args = [];
    { let curArg = arguments[0]; args.push(curArg); }
    return this.st.getItem(...args);
  }

  setItem(key, value) {
    if (arguments.length < 2) {
      throw new TypeError("Failed to execute 'setItem' on 'Storage': 2 arguments required, but only " + arguments.length + " present.");
    }
    const args = [];
    { let curArg = arguments[0]; args.push(curArg); }
    { let curArg = arguments[1]; args.push(curArg); }
    return this.st.setItem(...args);
  }

  removeItem(key) {
    if (arguments.length < 1) {
      throw new TypeError("Failed to execute 'removeItem' on 'Storage': 1 argument required, but only " + arguments.length + " present.");
    }
    const args = [];
    { let curArg = arguments[0]; args.push(curArg); }
    return this.st.removeItem(...args);
  }

  clear() {
    if (!this || !module.exports.is(this)) {
      throw new TypeError("Illegal invocation");
    }

    return this.st.clear();
  }

  get length() {
    if (!this || !module.exports.is(this)) {
      throw new TypeError("Illegal invocation");
    }

    return this.st["length"];
  }
}
Object.defineProperties(Storage.prototype, {
  key: { enumerable: true },
  getItem: { enumerable: true },
  setItem: { enumerable: true },
  removeItem: { enumerable: true },
  clear: { enumerable: true },
  length: { enumerable: true },
  [Symbol.toStringTag]: { value: "Storage", configurable: true }
});

class Navigator {
  javaEnabled() { return false; }
  get appCodeName() { return "Mozilla"; }
  get appName() { return "Netscape"; }
  get appVersion() { return "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"; }
  get platform() { return "Win32"; }
  get product() { return "Gecko"; }
  get productSub() { return "20030107"; }
  get userAgent() { return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"; }
  get vendor() { return "Google Inc."; }
  get vendorSub() { return ""; }
  get language() { return "en-US"; }
  get languages() { return ["en-US", "en"]; }
  get onLine() { return true; }
  get cookieEnabled() { return "true"; }
  get plugins() { return ["internal-pdf-viewer"]; }
  get mimeTypes() { return ["application/pdf", "text/pdf"]; }
  get hardwareConcurrency() { return 8; }
}
Object.defineProperties(Navigator.prototype, {
  javaEnabled: { enumerable: true },
  appCodeName: { enumerable: true },
  appName: { enumerable: true },
  appVersion: { enumerable: true },
  platform: { enumerable: true },
  product: { enumerable: true },
  productSub: { enumerable: true },
  userAgent: { enumerable: true },
  vendor: { enumerable: true },
  vendorSub: { enumerable: true },
  language: { enumerable: true },
  languages: { enumerable: true },
  onLine: { enumerable: true },
  cookieEnabled: { enumerable: true },
  plugins: { enumerable: true },
  mimeTypes: { enumerable: true },
  hardwareConcurrency: { enumerable: true },
  [Symbol.toStringTag]: { value: "Navigator", configurable: true }
});

function Window() {
  const window = this;
  this._globalProxy = this;
  let timers = Object.create(null);
  let animationFrameCallbacks = Object.create(null);
  this._document = {
    "origin": "https://captcha/",
    "body": {"innerText": "", "innerHTML": ""},
    "getElementById": () => {},
  };
  this._parent = this._top = this._globalProxy;
  this._length = 0;
  this._commonForOrigin = {
    [this._document.origin]: {
      localStorageArea: new Map(),
      sessionStorageArea: new Map(),
      windowsInSameOrigin: [this]
    }
  };

  this._currentOriginData = this._commonForOrigin[this._document.origin];

  this._localStorage = new Storage();
  this._sessionStorage = new Storage();
  const navigator = new Navigator();
  const screen = new Screen();

  define(this, {
    get length() { return window._length; },
    get window() { return window._globalProxy; },
    get frameElement() { return undefined; },
    get frames() { return window._globalProxy; },
    get self() { return window._globalProxy; },
    get parent() { return window._parent; },
    get top() { return window._top; },
    get document() { return window._document; },
    get navigator() { return navigator; },
    get screen() { return screen; },
    get localStorage() { return this._localStorage; },
    get sessionStorage() { return this._sessionStorage; }
  });

  let latestTimerId = 0;
  let latestAnimationFrameCallbackId = 0;

  this.setTimeout = function (fn, ms) {
    const args = [];
    for (let i = 2; i < arguments.length; ++i) {
      args[i - 2] = arguments[i];
    }
    return startTimer(window, setTimeout, clearTimeout, ++latestTimerId, fn, ms, timers, args);
  };
  this.setInterval = function (fn, ms) {
    const args = [];
    for (let i = 2; i < arguments.length; ++i) {
      args[i - 2] = arguments[i];
    }
    return startTimer(window, setInterval, clearInterval, ++latestTimerId, fn, ms, timers, args);
  };
  this.clearInterval = stopTimer.bind(this, timers);
  this.clearTimeout = stopTimer.bind(this, timers);

  this.__stopAllTimers = function () {
    stopAllTimers(timers);
    stopAllTimers(animationFrameCallbacks);

    latestTimerId = 0;
    latestAnimationFrameCallbackId = 0;

    timers = Object.create(null);
    animationFrameCallbacks = Object.create(null);
  };

  this.atob = function (str) {
    if (arguments.length === 0) {
      throw new TypeError("1 argument required, but only 0 present.");
    }
    str = `${str}`;
    str = str.replace(/[ \t\n\f\r]/g, "");
    if (str.length % 4 === 0) {
      str = str.replace(/==?$/, "");
    }
    if (str.length % 4 === 1 || /[^+/0-9A-Za-z]/.test(str)) {
      return null;
    }
    let output = "";
    let buffer = 0;
    let accumulatedBits = 0;
    for (let i = 0; i < str.length; i++) {
      buffer <<= 6;
      let index = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".indexOf(str[i]);
      index = index < 0 ? undefined : index;
      buffer |= index;
      accumulatedBits += 6;
      if (accumulatedBits === 24) {
        output += String.fromCharCode((buffer & 0xff0000) >> 16);
        output += String.fromCharCode((buffer & 0xff00) >> 8);
        output += String.fromCharCode(buffer & 0xff);
        buffer = accumulatedBits = 0;
      }
    }
    if (accumulatedBits === 12) {
      buffer >>= 4;
      output += String.fromCharCode(buffer);
    } else if (accumulatedBits === 18) {
      buffer >>= 2;
      output += String.fromCharCode((buffer & 0xff00) >> 8);
      output += String.fromCharCode(buffer & 0xff);
    }
    if (output === null) {
      throw "The string to be decoded contains invalid characters.";
    }
    return output;
  };
  this.btoa = function (str) {
    if (arguments.length === 0) {
      throw new TypeError("1 argument required, but only 0 present.");
    }
    let i;
    str = `${str}`;
    for (i = 0; i < str.length; i++) {
      if (str.charCodeAt(i) > 255) {
        return null;
      }
    }
    let out = "";
    for (i = 0; i < str.length; i += 3) {
      const groupsOfSix = [undefined, undefined, undefined, undefined];
      groupsOfSix[0] = str.charCodeAt(i) >> 2;
      groupsOfSix[1] = (str.charCodeAt(i) & 0x03) << 4;
      if (str.length > i + 1) {
        groupsOfSix[1] |= str.charCodeAt(i + 1) >> 4;
        groupsOfSix[2] = (str.charCodeAt(i + 1) & 0x0f) << 2;
      }
      if (str.length > i + 2) {
        groupsOfSix[2] |= str.charCodeAt(i + 2) >> 6;
        groupsOfSix[3] = str.charCodeAt(i + 2) & 0x3f;
      }
      for (let j = 0; j < groupsOfSix.length; j++) {
        if (typeof groupsOfSix[j] === "undefined") {
          out += "=";
        } else {
          let index = groupsOfSix[j];
          if (index >= 0 && index < 64) {
            out += "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[index];
          }
        }
      }
    }
    if (out === null) {
      throw "The string to be encoded contains invalid characters.";
    }
    return out;
  };
  this.ArrayBuffer = ArrayBuffer;
  this.Int8Array = Int8Array;
  this.Uint8Array = Uint8Array;
  this.Uint8ClampedArray = Uint8ClampedArray;
  this.Int16Array = Int16Array;
  this.Uint16Array = Uint16Array;
  this.Int32Array = Int32Array;
  this.Uint32Array = Uint32Array;
  this.Float32Array = Float32Array;
  this.Float64Array = Float64Array;
  this.stop = () => {};
  this.close = function () {
    const currentWindow = this;
    (function windowCleaner(windowToClean) {
      for (let i = 0; i < windowToClean.length; i++) {
        windowCleaner(windowToClean[i]);
      }
      if (windowToClean !== currentWindow) {
        windowToClean.close();
      }
    }(this));
    if (this._document) {
      delete this._document;
    }
    this.__stopAllTimers();
  };
  this.getComputedStyle = () => {};
  this.captureEvents = () => {};
  this.releaseEvents = () => {};
  this.console = {
    assert: () => {},
    clear: () => {},
    count: () => {},
    countReset: () => {},
    debug: () => {},
    dir: () => {},
    dirxml: () => {},
    error: () => {},
    group: () => {},
    groupCollapsed: () => {},
    groupEnd: () => {},
    info: () => {},
    log: () => {},
    table: () => {},
    time: () => {},
    timeEnd: () => {},
    trace: () => {},
    warn: () => {}
  };
  define(this, {
    name: "",
    status: "",
    devicePixelRatio: 1,
    innerWidth: 1920,
    innerHeight: 951,
    outerWidth: 1920,
    outerHeight: 1080,
    pageXOffset: 0,
    pageYOffset: 0,
    screenX: 0,
    screenLeft: 0,
    screenY: 0,
    screenTop: 0,
    scrollX: 0,
    scrollY: 0,

    alert: () => {},
    blur: () => {},
    confirm: () => { return true; },
    focus: () => {},
    moveBy: () => {},
    moveTo: () => {},
    open: () => {},
    print: () => {},
    prompt: () => { return ""; },
    resizeBy: () => {},
    resizeTo: () => {},
    scroll: () => {},
    scrollBy: () => {},
    scrollTo: () => {}
  });
  process.nextTick(() => {
    if (!window.document) {
      return;
    }
  });
}

Object.defineProperty(Window.prototype, Symbol.toStringTag, {
  value: "Window",
  writable: false,
  enumerable: false,
  configurable: true
});
function startTimer(window, startFn, stopFn, timerId, callback, ms, timerStorage, args) {
  if (!window || !window._document) {
    return undefined;
  }
  if (typeof callback !== "function") {
    const code = String(callback);
    callback = window._globalProxy.eval.bind(window, code + `\n//# sourceURL=${window.location.href}`);
  }

  const oldCallback = callback;
  callback = () => {
    try {
      oldCallback.apply(window._globalProxy, args);
    } catch (e) {}
  };

  const res = startFn(callback, ms);
  timerStorage[timerId] = [res, stopFn];
  return timerId;
}

function stopTimer(timerStorage, id) {
  const timer = timerStorage[id];
  if (timer) {
    timer[1].call(undefined, timer[0]);
    delete timerStorage[id];
  }
}
function stopAllTimers(timers) {
  Object.keys(timers).forEach(key => {
    const timer = timers[key];
    timer[1].call(undefined, timer[0]);
  });
}