class LegalAIClient {
  constructor() {
    this.apiBaseUrl = "/api/v1";
    this.chatMessages = document.getElementById("chat-messages");
    this.userInput = document.getElementById("user-input");
    this.sendButton = document.getElementById("send-button");
    this.uploadButton = document.getElementById("upload-button");
    this.documentUpload = document.getElementById("document-upload");
    this.systemStatus = document.getElementById("system-status");
    this.recentSources = document.getElementById("recent-sources");

    // Import Marked.js for markdown rendering
    this.loadMarkedLibrary();

    this.initializeEventListeners();
    this.checkSystemStatus();
    this.setupAutoResize();
  }

  loadMarkedLibrary() {
    const script = document.createElement("script");
    script.src =
      "https://cdnjs.cloudflare.com/ajax/libs/marked/4.3.0/marked.min.js";
    script.integrity =
      "sha512-ABCJjt3J7B/Uf/PeuLNzJv+LeRX0jJ+T93BNzjmt6deRGaw5X6Tt4SaCBjFEWz9wGy+NQUoD8jWN3UwJPxzBtA==";
    script.crossOrigin = "anonymous";
    script.referrerPolicy = "no-referrer";
    script.onload = () => {
      console.log("Marked.js loaded successfully");
      // Initialize marked with the options we want
      marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        sanitize: true,
      });
    };
    document.head.appendChild(script);

    // Add highlight.js for code syntax highlighting
    const highlightCSS = document.createElement("link");
    highlightCSS.rel = "stylesheet";
    highlightCSS.href =
      "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/github.min.css";
    document.head.appendChild(highlightCSS);

    const highlightJS = document.createElement("script");
    highlightJS.src =
      "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js";
    highlightJS.onload = () => {
      console.log("Highlight.js loaded successfully");
    };
    document.head.appendChild(highlightJS);
  }

  initializeEventListeners() {
    this.sendButton.addEventListener("click", () => this.sendMessage());
    this.userInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    this.uploadButton.addEventListener("click", () =>
      this.documentUpload.click()
    );
    this.documentUpload.addEventListener("change", (e) =>
      this.handleFileUpload(e)
    );
  }

  setupAutoResize() {
    this.userInput.addEventListener("input", () => {
      this.userInput.style.height = "auto";
      this.userInput.style.height = this.userInput.scrollHeight + "px";
    });
  }

  async checkSystemStatus() {
    try {
      const response = await fetch(`${this.apiBaseUrl}/health`);
      const data = await response.json();

      const statusDot = this.systemStatus.querySelector(".status-dot");
      const statusText = this.systemStatus.querySelector(".status-text");

      if (data.status === "healthy") {
        statusDot.classList.add("healthy");
        statusDot.classList.remove("error");
        statusText.textContent = "System Healthy";
      } else {
        statusDot.classList.add("error");
        statusDot.classList.remove("healthy");
        statusText.textContent = "System Error";
      }
    } catch (error) {
      console.error("Error checking system status:", error);
    }
  }

  async sendMessage() {
    const message = this.userInput.value.trim();
    if (!message) return;

    // Add user message to chat
    this.addMessage(message, "user");
    this.userInput.value = "";
    this.userInput.style.height = "auto";

    // Show typing indicator
    const typingIndicator = this.createTypingIndicator();
    this.chatMessages.appendChild(typingIndicator);
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

    try {
      const response = await fetch(`${this.apiBaseUrl}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });

      const data = await response.json();

      // Remove typing indicator
      typingIndicator.remove();

      // Add AI response to chat
      this.addMessage(data.response, "assistant", data.sources);

      // Update recent sources
      this.updateRecentSources(data.sources);
    } catch (error) {
      console.error("Error sending message:", error);
      this.addMessage(
        "Sorry, there was an error processing your request.",
        "assistant"
      );
    }
  }

  async handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${this.apiBaseUrl}/ingest`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      this.addMessage(
        `Document "${file.name}" uploaded successfully.`,
        "system"
      );
    } catch (error) {
      console.error("Error uploading file:", error);
      this.addMessage("Error uploading document. Please try again.", "system");
    }
  }

  addMessage(content, sender, sources = []) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${sender}`;

    const messageContent = document.createElement("div");
    messageContent.className = "message-content";

    // Render markdown if it's an assistant message and marked.js is loaded
    if (sender === "assistant" && window.marked) {
      // Use innerHTML when rendering markdown
      messageContent.innerHTML = marked.parse(content);

      // Apply syntax highlighting to code blocks if highlight.js is loaded
      if (window.hljs) {
        messageContent.querySelectorAll("pre code").forEach((block) => {
          hljs.highlightElement(block);
        });
      }
    } else {
      // Use textContent for user messages (no markdown)
      messageContent.textContent = content;
    }

    const timestamp = document.createElement("div");
    timestamp.className = "message-timestamp";
    timestamp.textContent = new Date().toLocaleTimeString();

    messageDiv.appendChild(messageContent);
    messageDiv.appendChild(timestamp);

    if (sources.length > 0) {
      const sourcesDiv = document.createElement("div");
      sourcesDiv.className = "message-sources";
      sourcesDiv.textContent = `Sources: ${sources.join(", ")}`;
      messageDiv.appendChild(sourcesDiv);
    }

    this.chatMessages.appendChild(messageDiv);
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
  }

  createTypingIndicator() {
    const indicator = document.createElement("div");
    indicator.className = "typing-indicator";

    for (let i = 0; i < 3; i++) {
      const dot = document.createElement("div");
      dot.className = "typing-dot";
      indicator.appendChild(dot);
    }

    return indicator;
  }

  updateRecentSources(sources) {
    this.recentSources.innerHTML = "";

    sources.forEach((source) => {
      const sourceItem = document.createElement("div");
      sourceItem.className = "source-item";
      sourceItem.textContent = source;
      this.recentSources.appendChild(sourceItem);
    });
  }
}

// Initialize the client when the DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  new LegalAIClient();
});
