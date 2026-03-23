"use client";

import { useState, useRef } from "react";
import Image from "next/image";

interface MessageContent {
  type: string;
  text?: string;
  image_url?: { url: string };
}

interface Message {
  role: string;
  content: string | MessageContent[];
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setUploadedImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
    // Reset the input value so the same file can be selected again
    event.target.value = "";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() && !uploadedImage) return;

    const userMessage: Message = {
      role: "user",
      content: uploadedImage
        ? [
            { type: "text", text: input || "What's in this image?" },
            { type: "image_url", image_url: { url: uploadedImage } },
          ]
        : input,
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setUploadedImage(null);
    setLoading(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: newMessages }),
      });

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      setMessages([...newMessages, { role: "assistant", content: data.response }]);
    } catch (error) {
      console.error("Error:", error);
      setMessages([
        ...newMessages,
        { role: "assistant", content: `Error: ${error}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <header className="bg-white border-b p-4">
        <h1 className="text-xl font-semibold">Image Analysis Agent</h1>
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-2xl p-3 rounded-lg ${
                msg.role === "user"
                  ? "bg-blue-500 text-white"
                  : "bg-white border"
              }`}
            >
              {Array.isArray(msg.content) ? (
                <div>
                  {msg.content.map((item: MessageContent, i: number) => (
                    <div key={i}>
                      {item.type === "text" && <p>{item.text}</p>}
                      {item.type === "image_url" && item.image_url?.url && (
                        <Image
                          src={item.image_url.url}
                          alt="Uploaded"
                          className="max-w-xs rounded mt-2"
                          width={300}
                          height={300}
                        />
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border p-3 rounded-lg">Thinking...</div>
          </div>
        )}
      </div>

      <div className="border-t bg-white p-4">
        {uploadedImage && (
          <div className="mb-2 flex items-center space-x-2">
            <Image
              src={uploadedImage}
              alt="Preview"
              className="w-16 h-16 rounded object-cover"
              width={64}
              height={64}
            />
            <button
              onClick={() => setUploadedImage(null)}
              className="text-sm text-red-600"
            >
              Remove
            </button>
          </div>
        )}
        <form onSubmit={handleSubmit} className="flex space-x-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageUpload}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="p-2 border rounded hover:bg-gray-100"
          >
            📎
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 p-2 border rounded"
          />
          <button
            type="submit"
            disabled={loading || (!input.trim() && !uploadedImage)}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
