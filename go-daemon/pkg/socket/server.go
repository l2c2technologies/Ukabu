// Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
//
// For licensing inquiries, contact:
// Indranil Das Gupta <indradg@l2c2.co.in>

package socket

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"sync"
)

type Logger interface {
	Log(level, event string, fields map[string]interface{})
}

type Tracker interface {
	RecordFailure(ip, domain, reason string) (int, bool)
	RecordSuccess(ip, domain string)
}

type Message struct {
	Type      string `json:"type"`      // "failure" or "success"
	IP        string `json:"ip"`
	Domain    string `json:"domain"`
	Reason    string `json:"reason,omitempty"`    // for failure: "invalid_solution", "timeout", "hmac_failed"
	Timestamp string `json:"timestamp"`
}

type Response struct {
	StrikeCount int    `json:"strike_count"`
	Blocked     bool   `json:"blocked"`
	Message     string `json:"message,omitempty"`
}

type Server struct {
	socketPath string
	tracker    Tracker
	logger     Logger
	listener   net.Listener
	wg         sync.WaitGroup
}

func NewServer(socketPath string, tracker Tracker, logger Logger) *Server {
	return &Server{
		socketPath: socketPath,
		tracker:    tracker,
		logger:     logger,
	}
}

func (s *Server) Start(ctx context.Context) error {
	// Remove existing socket if present
	os.Remove(s.socketPath)

	// Ensure directory exists
	dir := "/var/run/ukabu"
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to create socket directory: %w", err)
	}

	// Create Unix socket
	listener, err := net.Listen("unix", s.socketPath)
	if err != nil {
		return fmt.Errorf("failed to create Unix socket: %w", err)
	}
	s.listener = listener

	// Set socket permissions (readable by nginx user)
	if err := os.Chmod(s.socketPath, 0666); err != nil {
		s.logger.Log("warn", "socket_chmod_failed", map[string]interface{}{
			"error": err.Error(),
		})
	}

	s.logger.Log("info", "socket_server_started", map[string]interface{}{
		"path": s.socketPath,
	})

	// Accept connections
	for {
		select {
		case <-ctx.Done():
			return nil
		default:
			conn, err := listener.Accept()
			if err != nil {
				select {
				case <-ctx.Done():
					return nil
				default:
					s.logger.Log("error", "socket_accept_failed", map[string]interface{}{
						"error": err.Error(),
					})
					continue
				}
			}

			s.wg.Add(1)
			go s.handleConnection(conn)
		}
	}
}

func (s *Server) handleConnection(conn net.Conn) {
	defer s.wg.Done()
	defer conn.Close()

	scanner := bufio.NewScanner(conn)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}

		var msg Message
		if err := json.Unmarshal([]byte(line), &msg); err != nil {
			s.logger.Log("warn", "invalid_socket_message", map[string]interface{}{
				"error": err.Error(),
				"data":  line,
			})
			s.sendResponse(conn, Response{Message: "invalid JSON"})
			continue
		}

		s.handleMessage(conn, &msg)
	}

	if err := scanner.Err(); err != nil {
		s.logger.Log("error", "socket_read_error", map[string]interface{}{
			"error": err.Error(),
		})
	}
}

func (s *Server) handleMessage(conn net.Conn, msg *Message) {
	switch msg.Type {
	case "failure":
		strikeCount, blocked := s.tracker.RecordFailure(msg.IP, msg.Domain, msg.Reason)
		s.sendResponse(conn, Response{
			StrikeCount: strikeCount,
			Blocked:     blocked,
		})

	case "success":
		s.tracker.RecordSuccess(msg.IP, msg.Domain)
		s.sendResponse(conn, Response{
			StrikeCount: 0,
			Blocked:     false,
		})

	default:
		s.logger.Log("warn", "unknown_message_type", map[string]interface{}{
			"type": msg.Type,
		})
		s.sendResponse(conn, Response{Message: "unknown message type"})
	}
}

func (s *Server) sendResponse(conn net.Conn, resp Response) {
	data, err := json.Marshal(resp)
	if err != nil {
		s.logger.Log("error", "response_marshal_failed", map[string]interface{}{
			"error": err.Error(),
		})
		return
	}

	data = append(data, '\n')
	if _, err := conn.Write(data); err != nil {
		s.logger.Log("error", "response_write_failed", map[string]interface{}{
			"error": err.Error(),
		})
	}
}

func (s *Server) Stop() {
	if s.listener != nil {
		s.listener.Close()
	}
	s.wg.Wait()
	os.Remove(s.socketPath)
}
