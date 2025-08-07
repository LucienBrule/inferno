let extract = (item) => {
  const titleElement = item.querySelector('.s-item__title');
  const priceElement = item.querySelector('.s-item__price');
  const sellerElement = item.querySelector('.s-item__etrs-text');
  const subTitleElement = item.querySelector(".s-item__subtitle");
  const shippingElement = item.querySelector(".s-item__shipping");
  const quantityElement = item.querySelector(".s-item__quantitySold");
  const title = titleElement ? titleElement.textContent.trim() : 'N/A';
  const price = priceElement ? priceElement.textContent.trim() : 'N/A';
  const seller = sellerElement ? sellerElement.textContent.trim() : 'N/A';
  const subtitle = subTitleElement ? subTitleElement.textContent.trim() : 'N/A';
  const shipping = shippingElement ? shippingElement.textContent.trim() : 'N/A';
  const quantitySold = quantityElement ? quantityElement.textContent.trim(): 'N/A';
  return {
    title,
    price,
    seller,
    subtitle,
    shipping,
    quantitySold
  };
}