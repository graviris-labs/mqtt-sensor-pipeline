#!/usr/bin/env python3
"""
Advanced LIDAR Point Cloud Processing
Extends the basic visualizer with advanced processing capabilities.
"""
import numpy as np
import open3d as o3d
from scipy.spatial import Delaunay
import logging
from visualizer import LidarVisualizer

logger = logging.getLogger('advanced-visualizer')

class AdvancedLidarVisualizer(LidarVisualizer):
    """Extends LidarVisualizer with advanced processing capabilities"""
    
    def __init__(self, db_path=None):
        """Initialize with database path"""
        super().__init__(db_path)
        self.ground_plane = None
    
    def filter_outliers(self, points, nb_neighbors=20, std_ratio=2.0):
        """Filter outlier points using statistical outlier removal"""
        if len(points) < nb_neighbors + 1:
            logger.warning(f"Not enough points for outlier removal (need {nb_neighbors+1}, have {len(points)})")
            return points, np.arange(len(points))
        
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        
        # Perform statistical outlier removal
        try:
            cleaned, indices = pcd.remove_statistical_outlier(
                nb_neighbors=nb_neighbors, 
                std_ratio=std_ratio
            )
            
            # Convert back to numpy array
            filtered_points = np.asarray(cleaned.points)
            
            logger.info(f"Filtered {len(points) - len(filtered_points)} outlier points")
            return filtered_points, np.array(indices)
        except Exception as e:
            logger.error(f"Error in outlier removal: {e}")
            return points, np.arange(len(points))
    
    def segment_ground_plane(self, points, distance_threshold=10.0, ransac_n=3, num_iterations=100):
        """Segment ground plane from point cloud using RANSAC"""
        if len(points) < ransac_n:
            logger.warning(f"Not enough points for ground plane segmentation (need {ransac_n}, have {len(points)})")
            return points, np.array([]), np.array([])
        
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        
        try:
            # Apply RANSAC to find the ground plane
            plane_model, inliers = pcd.segment_plane(
                distance_threshold=distance_threshold,
                ransac_n=ransac_n,
                num_iterations=num_iterations
            )
            
            # Extract the plane equation (ax + by + cz + d = 0)
            [a, b, c, d] = plane_model
            
            # Store the ground plane parameters
            self.ground_plane = plane_model
            
            # Extract inlier and outlier points
            inlier_cloud = pcd.select_by_index(inliers)
            outlier_cloud = pcd.select_by_index(inliers, invert=True)
            
            # Convert back to numpy array
            inlier_points = np.asarray(inlier_cloud.points)
            outlier_points = np.asarray(outlier_cloud.points)
            
            logger.info(f"Ground plane segmentation: {len(inlier_points)} inliers, {len(outlier_points)} outliers")
            logger.info(f"Plane equation: {a:.3f}x + {b:.3f}y + {c:.3f}z + {d:.3f} = 0")
            
            return inlier_points, outlier_points, np.array(inliers)
        except Exception as e:
            logger.error(f"Error in ground plane segmentation: {e}")
            return points, np.array([]), np.array([])
    
    def cluster_points(self, points, eps=30.0, min_points=10):
        """Cluster points using DBSCAN clustering"""
        if len(points) < min_points:
            logger.warning(f"Not enough points for clustering (need {min_points}, have {len(points)})")
            return [], []
        
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        
        try:
            # Apply DBSCAN clustering
            labels = np.array(pcd.cluster_dbscan(eps=eps, min_points=min_points))
            
            # Find the unique cluster labels (excluding noise label -1)
            unique_labels = np.unique(labels)
            unique_labels = unique_labels[unique_labels >= 0]
            
            # Extract points for each cluster
            clusters = []
            for label in unique_labels:
                cluster_indices = np.where(labels == label)[0]
                cluster_points = points[cluster_indices]
                clusters.append(cluster_points)
            
            logger.info(f"Clustering found {len(clusters)} clusters")
            
            return clusters, labels
        except Exception as e:
            logger.error(f"Error in clustering: {e}")
            return [], []
    
    def create_mesh_from_points(self, points, alpha=0.5):
        """Create a mesh from points using Alpha Shapes"""
        if len(points) < 4:  # Minimum points for a tetrahedron
            logger.warning(f"Not enough points for mesh creation (need at least 4, have {len(points)})")
            return None
        
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        
        try:
            # Compute alpha shape
            # First compute the convex hull as a fallback
            mesh = o3d.geometry.TetraMesh.create_from_point_cloud(pcd)[0]
            
            # Then try to compute an alpha shape if we have enough points
            if len(points) > 10:
                alpha_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(pcd, alpha)
                if len(alpha_mesh.triangles) > 0:
                    mesh = alpha_mesh
            
            logger.info(f"Created mesh with {len(mesh.triangles)} triangles")
            return mesh
        except Exception as e:
            logger.error(f"Error in mesh creation: {e}")
            return None
    
    def calculate_object_dimensions(self, points):
        """Calculate dimensions of an object defined by points"""
        if len(points) < 3:
            logger.warning(f"Not enough points to calculate dimensions (need at least 3, have {len(points)})")
            return None
        
        try:
            # Find the min/max extents in each dimension
            min_coords = np.min(points, axis=0)
            max_coords = np.max(points, axis=0)
            
            # Calculate dimensions
            dimensions = max_coords - min_coords
            
            # Calculate center
            center = (min_coords + max_coords) / 2
            
            return {
                "center": center,
                "width": dimensions[0],
                "depth": dimensions[1],
                "height": dimensions[2],
                "min_coords": min_coords,
                "max_coords": max_coords
            }
        except Exception as e:
            logger.error(f"Error calculating object dimensions: {e}")
            return None
    
    def create_bounding_box(self, points):
        """Create an oriented bounding box for points"""
        if len(points) < 3:
            logger.warning(f"Not enough points for bounding box (need at least 3, have {len(points)})")
            return None
        
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        
        try:
            # Create axis-aligned bounding box
            aabb = pcd.get_axis_aligned_bounding_box()
            aabb.color = (1, 0, 0)  # Red
            
            # Create oriented bounding box (more closely fits the points)
            obb = pcd.get_oriented_bounding_box()
            obb.color = (0, 1, 0)  # Green
            
            logger.info(f"Created bounding boxes for points")
            return aabb, obb
        except Exception as e:
            logger.error(f"Error creating bounding box: {e}")
            return None, None
    
    def process_scan_with_advanced_features(self, timestamp=None, filter_outliers=True,
                                           segment_ground=True, cluster_objects=True):
        """Process scan with advanced features and return enhanced visualization"""
        # Get scan data
        if timestamp:
            scan_data = self.get_historical_scan(timestamp)
        else:
            scan_data = self.get_latest_scan()
        
        if not scan_data:
            return None, {}
        
        # Convert to points
        points, colors = self.convert_readings_to_points(scan_data)
        
        if points is None or len(points) == 0:
            return None, {}
        
        # Store original points for comparison
        original_points = points.copy()
        original_colors = colors.copy()
        
        # Results dictionary to store processing results
        results = {
            "timestamp": scan_data["timestamp"],
            "original_points": len(points),
            "filtered_points": 0,
            "ground_points": 0,
            "object_points": 0,
            "clusters": 0,
            "processing_results": {}
        }
        
        # Step 1: Filter outliers if requested
        if filter_outliers and len(points) > 20:
            filtered_points, indices = self.filter_outliers(points)
            filtered_colors = colors[indices]
            results["filtered_points"] = len(filtered_points)
            
            # Update points for further processing
            points = filtered_points
            colors = filtered_colors
        else:
            results["filtered_points"] = len(points)
        
        # Step 2: Segment ground plane if requested
        ground_points = np.array([])
        object_points = np.array([])
        ground_colors = np.array([])
        object_colors = np.array([])
        
        if segment_ground and len(points) > 3:
            ground_points, object_points, ground_indices = self.segment_ground_plane(points)
            
            if len(ground_indices) > 0:
                ground_colors = colors[ground_indices]
                
                # Create mask for objects (non-ground points)
                object_mask = np.ones(len(points), dtype=bool)
                object_mask[ground_indices] = False
                object_colors = colors[object_mask]
            
            results["ground_points"] = len(ground_points)
            results["object_points"] = len(object_points)
        
        # Step 3: Cluster objects if requested
        clusters = []
        cluster_colors = []
        
        if cluster_objects and len(object_points) > 10:
            clusters, labels = self.cluster_points(object_points)
            results["clusters"] = len(clusters)
            
            # Store cluster dimensions
            if len(clusters) > 0:
                cluster_dimensions = []
                
                for i, cluster in enumerate(clusters):
                    dims = self.calculate_object_dimensions(cluster)
                    
                    if dims:
                        cluster_dimensions.append({
                            "cluster_id": i,
                            "center": dims["center"].tolist(),
                            "width": dims["width"],
                            "depth": dims["depth"],
                            "height": dims["height"],
                            "point_count": len(cluster)
                        })
                
                results["processing_results"]["cluster_dimensions"] = cluster_dimensions
        
        # Create an enhanced visualization
        fig = self.create_enhanced_plotly_figure(
            original_points=original_points,
            original_colors=original_colors,
            ground_points=ground_points,
            ground_colors=ground_colors,
            object_points=object_points,
            object_colors=object_colors,
            clusters=clusters,
            timestamp=scan_data["timestamp"]
        )
        
        return fig, results
    
    def create_enhanced_plotly_figure(self, original_points, original_colors,
                                     ground_points, ground_colors,
                                     object_points, object_colors,
                                     clusters, timestamp):
        """Create an enhanced Plotly figure with segmented point cloud data"""
        import plotly.graph_objects as go
        
        # Create a new figure
        fig = go.Figure()
        
        # Add the original points with low opacity if we have segmented data
        if len(ground_points) > 0 or len(clusters) > 0:
            # Convert colors to format expected by Plotly
            colors_rgb = [f'rgb({int(r*255)},{int(g*255)},{int(b*255)})' for r, g, b in original_colors]
            
            fig.add_trace(go.Scatter3d(
                x=original_points[:, 0],
                y=original_points[:, 1],
                z=original_points[:, 2],
                mode='markers',
                marker=dict(
                    size=2,
                    color=colors_rgb,
                    opacity=0.3
                ),
                name='Original Points'
            ))
        
        # Add ground points if available
        if len(ground_points) > 0:
            # Convert colors to format expected by Plotly
            if len(ground_colors) > 0:
                colors_rgb = [f'rgb({int(r*255)},{int(g*255)},{int(b*255)})' for r, g, b in ground_colors]
            else:
                colors_rgb = 'rgb(0,255,0)'  # Green for ground
            
            fig.add_trace(go.Scatter3d(
                x=ground_points[:, 0],
                y=ground_points[:, 1],
                z=ground_points[:, 2],
                mode='markers',
                marker=dict(
                    size=3,
                    color=colors_rgb,
                    opacity=0.7
                ),
                name='Ground'
            ))
        
        # Add object points if available and no clusters
        if len(object_points) > 0 and len(clusters) == 0:
            # Convert colors to format expected by Plotly
            if len(object_colors) > 0:
                colors_rgb = [f'rgb({int(r*255)},{int(g*255)},{int(b*255)})' for r, g, b in object_colors]
            else:
                colors_rgb = 'rgb(255,0,0)'  # Red for objects
            
            fig.add_trace(go.Scatter3d(
                x=object_points[:, 0],
                y=object_points[:, 1],
                z=object_points[:, 2],
                mode='markers',
                marker=dict(
                    size=4,
                    color=colors_rgb,
                    opacity=0.8
                ),
                name='Objects'
            ))
        
        # Add clusters if available
        if len(clusters) > 0:
            # Define colors for clusters
            cluster_colors = [
                'rgb(255,0,0)', 'rgb(0,0,255)', 'rgb(255,255,0)', 
                'rgb(255,0,255)', 'rgb(0,255,255)', 'rgb(255,128,0)',
                'rgb(128,0,255)', 'rgb(0,255,128)', 'rgb(128,128,255)',
                'rgb(255,128,128)'
            ]
            
            for i, cluster in enumerate(clusters):
                color = cluster_colors[i % len(cluster_colors)]
                
                fig.add_trace(go.Scatter3d(
                    x=cluster[:, 0],
                    y=cluster[:, 1],
                    z=cluster[:, 2],
                    mode='markers',
                    marker=dict(
                        size=5,
                        color=color,
                        opacity=0.9
                    ),
                    name=f'Cluster {i+1}'
                ))
                
                # Calculate center of cluster
                center = np.mean(cluster, axis=0)
                
                # Add a slightly larger marker at the center of the cluster
                fig.add_trace(go.Scatter3d(
                    x=[center[0]],
                    y=[center[1]],
                    z=[center[2]],
                    mode='markers',
                    marker=dict(
                        size=10,
                        color=color,
                        symbol='diamond',
                        opacity=1.0
                    ),
                    name=f'Center {i+1}'
                ))
        
        # Add coordinate axes
        axis_length = 50  # A fixed length for better visibility
        
        # X-axis (red)
        fig.add_trace(go.Scatter3d(
            x=[0, axis_length], y=[0, 0], z=[0, 0],
            line=dict(color='red', width=4),
            name='X-axis'
        ))
        
        # Y-axis (green)
        fig.add_trace(go.Scatter3d(
            x=[0, 0], y=[0, axis_length], z=[0, 0],
            line=dict(color='green', width=4),
            name='Y-axis'
        ))
        
        # Z-axis (blue)
        fig.add_trace(go.Scatter3d(
            x=[0, 0], y=[0, 0], z=[0, axis_length],
            line=dict(color='blue', width=4),
            name='Z-axis'
        ))
        
        # Update layout
        fig.update_layout(
            title=f"LIDAR Point Cloud Analysis (Timestamp: {timestamp})",
            scene=dict(
                xaxis_title='X (cm)',
                yaxis_title='Y (cm)',
                zaxis_title='Z (cm)',
                aspectmode='data'  # Keep the aspect ratio true to the data
            ),
            legend=dict(
                x=0,
                y=1,
                traceorder="normal",
                font=dict(
                    family="sans-serif",
                    size=12,
                    color="black"
                ),
            ),
            margin=dict(l=0, r=0, b=0, t=40)
        )
        
        return fig