#!/usr/bin/env python3
"""
Flask Style Template - Example Application

This demonstrates how to use the beautiful styling template with:
- Advanced theming system (Dark, Light, Liquid Glass)
- Mobile-first responsive design
- PWA support
- Sidebar navigation
- Theme switching
"""

from flask import Flask, render_template, jsonify
import os

app = Flask(__name__)

# Sample data for demonstration
sample_posts = [
    {
        'id': 1,
        'title': 'Welcome to Flask Style Template',
        'content': 'This is a beautiful example of the advanced theming system with dark mode, light mode, and liquid glass effects.',
        'author': 'Flask Developer',
        'date': '2024-01-15',
        'likes': 42,
        'comments': 8
    },
    {
        'id': 2,
        'title': 'Mobile-First Design',
        'content': 'Perfect mobile experience with responsive images, touch gestures, and iOS Safari optimizations.',
        'author': 'UI Designer',
        'date': '2024-01-14',
        'likes': 38,
        'comments': 12
    },
    {
        'id': 3,
        'title': 'Liquid Glass Theme',
        'content': 'Stunning glass morphism effects with backdrop blur and semi-transparent elements.',
        'author': 'Theme Creator',
        'date': '2024-01-13',
        'likes': 56,
        'comments': 15
    }
]

sample_messages = [
    {
        'id': 1,
        'sender': 'Alice',
        'content': 'Hey! How is the new Flask template working?',
        'timestamp': '2024-01-15 10:30',
        'avatar': '👩‍💻'
    },
    {
        'id': 2,
        'sender': 'Bob',
        'content': 'The dark mode looks amazing! Love the purple gradient.',
        'timestamp': '2024-01-15 10:32',
        'avatar': '👨‍💻'
    },
    {
        'id': 3,
        'sender': 'Alice',
        'content': 'The mobile experience is perfect too. No more scrolling issues!',
        'timestamp': '2024-01-15 10:35',
        'avatar': '👩‍💻'
    }
]

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html', posts=sample_posts[:2])

@app.route('/messages')
def messages():
    """Messages page"""
    return render_template('messages.html', messages=sample_messages)

@app.route('/channels')
def channels():
    """Channels page"""
    return render_template('channels.html', channels=[
        {'name': 'General', 'messages': 156, 'active': True},
        {'name': 'Development', 'messages': 89, 'active': False},
        {'name': 'Design', 'messages': 234, 'active': False}
    ])

@app.route('/feed')
def feed():
    """Social feed page"""
    return render_template('feed.html', posts=sample_posts)

@app.route('/profile')
def profile():
    """Profile page"""
    return render_template('profile.html', user={
        'name': 'Flask Developer',
        'email': 'developer@flask.com',
        'avatar': '👨‍💻',
        'bio': 'Building beautiful web applications with Flask and modern CSS.'
    })

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')

@app.route('/api/theme', methods=['POST'])
def update_theme():
    """API endpoint for theme updates (example)"""
    return jsonify({'status': 'success', 'message': 'Theme updated'})

if __name__ == '__main__':
    # Development server
    app.run(debug=True, host='0.0.0.0', port=5000) 