(()=>{
document.getElementsByClassName('dataform-input')[0].style.opacity = "1";
const global = {};
z = document.getElementById.bind(document);

const FILECHECK = { "name": "ArtemisPlayerInfo.sav", "script": "/Script/Artemis.ArtemisPlayerInfoSaveGame"}

const saveData = {}

const app = z("app")
const modal = z("app-modal")
const modalContent = z("modal-part")

function downloadSave() {
	var blob = new Blob([global.data]),
		url = window.URL.createObjectURL(blob),
		a = document.createElement("a");
	a.style = "display: none";
	document.body.appendChild(a);
	a.href = url;
	a.download = global.fname;
	a.click();
	a.parentNode.removeChild(a);
	window.URL.revokeObjectURL(url);
}

const fdi = z('fdinfo')
function validateFile(data) {
	let ofs = data.find("/Script/Artemis", 16)
	if (ofs < 0)
		return false

	let len = global.data.getInt32(ofs - 4, true)
	let name
	[ len, name ] = global.data.readString(ofs, len);

	return name == FILECHECK.script
}
(()=>{
	let c = document.querySelector('#filedropper > code')
	c.innerText = FILECHECK.name
})()
function errorShake() {
	fdi.classList.remove('error')
	setTimeout(function() {
		fdi.style.opacity = "1";
		fdi.style.top = "calc(70% + 50px)";
		fd.classList.add('error')
		fdi.classList.add('error')
		fd.style.border = '';
	}, 5);
}

function readSave() {
	let ofs = 0x480;

	let prem = global.data.find('UnlockedDrivePasses\0\x0E\0\0\0ArrayProperty\0\x08\0\0\0\0\0\0\0\x0D\0\0\0BoolProperty\0\0')
	var isPremium = []
	if (prem > 1) {
		prem += 0x40
		let sz = global.data.getUint32(prem, true)
		prem += 4
		for (; sz > 0; sz--) {
			isPremium.push(global.data.getUint8(prem, true) > 0)
			prem += 1
		}
	}
	console.log(isPremium)
	
	ofs = global.data.find('DXPList\0\x0E\0\0\0ArrayProperty\0')
	if (ofs > 0) {
		ofs += 0x33
		let sz = global.data.getUint32(ofs, true)
		ofs += 4
		modalContent.innerHTML = ""
		for (let i = 0; i < sz; i++) {
			let c = ""
			if (isPremium[i]) {
				c = `Set Premium DrivePass ${i+1} Level to 100` 
				global.data.setUint32(ofs + 4 * i, 150000, true)
			} else {
				c = `Set DrivePass ${i+1} Level to 99` 
				global.data.setUint32(ofs + 4 * i, 149000, true)
			}
			let s = document.createElement("li")
			s.innerText = c
			modalContent.appendChild(s)
		}

		let _div = document.createElement("div")
		_div.classList.add("modal-download-button")
		
		let _btn = document.createElement("button")
		_btn.textContent = "Download Save"
		_btn.addEventListener("click", downloadSave);
		
		_div.appendChild(_btn)

		modalContent.parentNode.appendChild(_div)
	} else {
		modalContent.textContent = `Unable to change DrivePass Level` 
	}
}

function loadFile(f = null) {
	var fr;
	if (z('fileinput').files[0]) f = z('fileinput').files[0];
	if (f != null) {
		global.fname = f.name;
		fr = new FileReader();
		fr.readAsBinaryString(f);
		var dr = new FileReader();
		
		global.dec = new TextDecoder("ISO-8859-2");
		global.utfdec = new TextDecoder("UTF-16");
		
		dr.readAsArrayBuffer(f);
		dr.onload = function(f) { 
			global.data = new DataView(f.target.result);
			
			global.data.readString = function (offset, length) {
				let blen = length
				
				if (length > 0) {
					var chars = new Uint8Array(length - 1), i, j;
					for (i = offset, j=0; j < length; i++) chars[j++] = this.getInt8(i, true);
					return [ blen, global.dec.decode(chars) ]
				} else {
					blen *= -2
					let enc_len = blen - 2
					var chars = new Uint16Array(enc_len / 2), i, j;
					for (i = offset, j=0; j < enc_len; i += 2) chars[j++] = this.getUint16(i, true);
					return [ blen, global.utfdec.decode(chars) ]
				}
			}
			
			global.data.writeString = function (offset, string, size=string.length) {
				var chars = new Uint8Array(size), i, j;
				for (j = 0; j < string.length; j++) chars[j] = string.charCodeAt(j);
				for (i = offset, j=0; j < size; i++) this.setInt8(i, chars[j++], true);
			}
			
			global.data.setFloat = function (offset, value, littleEndian = true) {
				return this.setFloat32(offset, value, littleEndian)
			}
			
			global.data.getFloat = function (offset, littleEndian = true) {
				let v = this.getFloat32(offset, littleEndian)
				
				return v // Math.round(v * 1000) / 1000;
			}
			
			global.data.find = function (pattern, start = 0) {
				return this.str.indexOf(pattern, start)
			}
			
			var u8arr = new Uint8Array(global.data.buffer);
			global.data.str = global.dec.decode(u8arr)
			
			if (validateFile(global.data)) {
				var md = document.getElementsByClassName('dataform-input')[0];
				md.style.opacity = "0";
				modal.style.display = "block"
				setTimeout(function() {
					md.parentNode.removeChild(md);
				}, 300);
				readSave()
			} else {
				errorShake()
			}
		}
	}
}
function handleFileSelect(evt) {
	evt.stopPropagation();
	evt.preventDefault();
	loadFile(evt.dataTransfer.files[0]);
}
function handleDragOver(evt) {
	fd.style.border = '2px solid #bbb';
	evt.stopPropagation();
	evt.preventDefault();
	evt.dataTransfer.dropEffect = 'copy';
}
function handleDragOut(evt) {
	fd.style.border = '';
}
var fd = z('filedropper');
fd.addEventListener('dragover', handleDragOver, false);
fd.addEventListener('dragleave', handleDragOut, false);
fd.addEventListener('drop', handleFileSelect, false);
fd.addEventListener('click', function() { z('fileinput').click()}, false);
z('fileinput').addEventListener('change', loadFile, false);		

document.addEventListener('contextmenu', function(e) {
	e.preventDefault();
}, false);
})();