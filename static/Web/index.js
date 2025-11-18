const dropArea = document.querySelector(".drag-area");
const dragText = document.querySelector(".header");
let button = dropArea.querySelector(".button");
let input = dropArea.querySelector("input");
console.info(input);

button.onclick = () => {
  input.click();
};
// when browse
