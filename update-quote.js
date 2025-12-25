const fs = require('fs');

async function updateQuote() {
  try {
    const quotes = require('./quotes.json');
    const randomIndex = Math.floor(Math.random() * quotes.length);
    const { quote, author } = quotes[randomIndex];

    // Encode strings for URL safety
    const safeQuote = encodeURIComponent(quote);
    const safeAuthor = encodeURIComponent(author);

    // 1. Configuration for Dark Mode (Keeps your original dark colors)
    const darkUrl = `https://readme-daily-quotes.vercel.app/api?author=${safeAuthor}&quote=${safeQuote}&theme=dark&bg_color=220a28&author_color=ffeb95&accent_color=c56a90`;

    // 2. Configuration for Light Mode (White background, dark text)
    // You can adjust hex colors here: bg_color (background), author_color (text), accent_color (decoration)
    const lightUrl = `https://readme-daily-quotes.vercel.app/api?author=${safeAuthor}&quote=${safeQuote}&theme=light&bg_color=ffffff&author_color=333333&accent_color=005b96`;

    // 3. Create HTML structure supporting auto-switching based on user preference
    // The <picture> tag allows GitHub to choose the image based on system theme (dark/light)
    const cardDesign = `
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="${darkUrl}">
    <img src="${lightUrl}" alt="Daily Quote">
  </picture>
</p>
`;

    const readmePath = './README.md';
    let readmeContent = fs.readFileSync(readmePath, 'utf-8');

    // Replace the old card content with the new design
    readmeContent = readmeContent.replace(
      /(.|\n)*/,
      cardDesign
    );

    fs.writeFileSync(readmePath, readmeContent);
    console.log('Quote updated successfully!');
  } catch (error) {
    console.error('Error updating quote:', error);
  }
}

updateQuote();