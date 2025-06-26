"""
Analytics Engine for InvoiceGenius AI
====================================

This module transforms raw invoice data into valuable business insights and intelligence.
Think of this as your personal business analyst who can look at all your invoice data
and tell you interesting patterns, trends, and opportunities for optimization.

Why analytics matter for invoice processing?
- Cost Management: Identify spending patterns and optimize vendor relationships
- Cash Flow: Understand payment cycles and plan better
- Vendor Performance: Track which vendors provide best value and service
- Compliance: Monitor for unusual patterns that might indicate fraud
- Business Intelligence: Extract insights that drive strategic decisions

This module provides multiple levels of analysis:
1. Descriptive Analytics: What happened? (summaries, trends)
2. Diagnostic Analytics: Why did it happen? (correlations, patterns)
3. Predictive Analytics: What might happen? (forecasts, predictions)
4. Prescriptive Analytics: What should we do? (recommendations)
"""

import logging
import sqlite3
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import json

# Statistical analysis
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression

# Our custom modules
from config import Config

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """
    Comprehensive business analytics and intelligence engine
    
    This class analyzes invoice data to provide actionable business insights.
    It goes beyond simple reporting to identify patterns, anomalies, and
    opportunities that can drive better business decisions.
    
    Think of this as having a team of data scientists and business analysts
    working around the clock to understand your invoice data.
    """
    
    def __init__(self, database_manager):
        """Initialize analytics engine with database connection"""
        self.config = Config()
        self.db_manager = database_manager
        
        # Cache for expensive calculations
        self._cache = {}
        self._cache_expiry = {}
        self.cache_duration = timedelta(hours=1)  # Cache results for 1 hour
        
        logger.info("Analytics engine initialized")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data with key metrics and insights
        
        This provides the main overview data for executive dashboards and
        general business monitoring.
        
        Returns:
            Dictionary containing all key metrics and KPIs
        """
        try:
            cache_key = "dashboard_data"
            if self._is_cached(cache_key):
                return self._cache[cache_key]
            
            dashboard_data = {}
            
            # Basic metrics
            dashboard_data.update(self._get_basic_metrics())
            
            # Trend analysis
            dashboard_data.update(self._get_trend_metrics())
            
            # Vendor analysis
            dashboard_data.update(self._get_vendor_metrics())
            
            # Performance metrics
            dashboard_data.update(self._get_performance_metrics())
            
            # Financial insights
            dashboard_data.update(self._get_financial_insights())
            
            # Alert and anomaly data
            dashboard_data.update(self._get_alerts_and_anomalies())
            
            # Cache the results
            self._cache[cache_key] = dashboard_data
            self._cache_expiry[cache_key] = datetime.now() + self.cache_duration
            
            logger.info("Dashboard data compiled successfully")
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to compile dashboard data: {str(e)}")
            return self._get_fallback_dashboard_data()
    
    def _get_basic_metrics(self) -> Dict[str, Any]:
        """Get fundamental business metrics"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_invoices,
                        SUM(total_amount) as total_amount,
                        AVG(total_amount) as average_amount,
                        MIN(invoice_date) as earliest_date,
                        MAX(invoice_date) as latest_date,
                        COUNT(DISTINCT vendor_name) as unique_vendors
                    FROM invoices 
                    WHERE total_amount IS NOT NULL
                """)
                
                result = cursor.fetchone()
                
                # Calculate this month vs last month
                current_month_data = self._get_monthly_comparison()
                
                return {
                    'total_invoices': result[0] or 0,
                    'total_amount': result[1] or 0.0,
                    'average_amount': result[2] or 0.0,
                    'earliest_date': result[3],
                    'latest_date': result[4],
                    'unique_vendors': result[5] or 0,
                    'invoices_this_month': current_month_data['this_month'],
                    'invoices_last_month': current_month_data['last_month'],
                    'amount_change': current_month_data['amount_change']
                }
                
        except Exception as e:
            logger.error(f"Failed to get basic metrics: {str(e)}")
            return {
                'total_invoices': 0, 'total_amount': 0.0, 'average_amount': 0.0,
                'unique_vendors': 0, 'invoices_this_month': 0, 'invoices_last_month': 0,
                'amount_change': 0.0
            }
    
    def _get_trend_metrics(self) -> Dict[str, Any]:
        """Analyze trends and patterns over time"""
        try:
            # Monthly trend analysis
            monthly_trends = self.get_monthly_trend()
            
            # Calculate growth rates
            growth_rate = 0.0
            if len(monthly_trends) >= 2:
                recent_months = sorted(monthly_trends, key=lambda x: x['month'])[-2:]
                if len(recent_months) == 2:
                    old_count = recent_months[0]['count']
                    new_count = recent_months[1]['count']
                    if old_count > 0:
                        growth_rate = ((new_count - old_count) / old_count) * 100
            
            # Seasonal analysis
            seasonal_patterns = self._analyze_seasonal_patterns()
            
            return {
                'monthly_trends': monthly_trends,
                'growth_rate': growth_rate,
                'seasonal_patterns': seasonal_patterns,
                'trend_direction': 'up' if growth_rate > 5 else 'down' if growth_rate < -5 else 'stable'
            }
            
        except Exception as e:
            logger.error(f"Failed to get trend metrics: {str(e)}")
            return {'monthly_trends': [], 'growth_rate': 0.0, 'seasonal_patterns': {}}
    
    def _get_vendor_metrics(self) -> Dict[str, Any]:
        """Analyze vendor-related metrics and relationships"""
        try:
            vendor_distribution = self.get_vendor_distribution()
            vendor_performance = self._analyze_vendor_performance()
            vendor_concentration = self._calculate_vendor_concentration()
            
            return {
                'vendor_distribution': vendor_distribution,
                'vendor_performance': vendor_performance,
                'vendor_concentration': vendor_concentration,
                'top_vendors': vendor_distribution[:5] if vendor_distribution else []
            }
            
        except Exception as e:
            logger.error(f"Failed to get vendor metrics: {str(e)}")
            return {'vendor_distribution': [], 'vendor_performance': {}, 'vendor_concentration': 0}
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get AI processing performance metrics"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        AVG(confidence) as avg_confidence,
                        AVG(validation_score) as avg_validation_score,
                        AVG(processing_time) as avg_processing_time,
                        COUNT(CASE WHEN confidence > 0.9 THEN 1 END) as high_confidence_count,
                        COUNT(CASE WHEN confidence < 0.7 THEN 1 END) as low_confidence_count
                    FROM invoices 
                    WHERE confidence IS NOT NULL
                """)
                
                result = cursor.fetchone()
                total_invoices = self.db_manager.get_total_invoices()
                
                return {
                    'avg_confidence': result[0] or 0.0,
                    'avg_validation_score': result[1] or 0.0,
                    'avg_processing_time': result[2] or 0.0,
                    'success_rate': (result[2] / total_invoices) if total_invoices > 0 else 0.0,
                    'high_confidence_percentage': (result[3] / total_invoices * 100) if total_invoices > 0 else 0.0,
                    'low_confidence_percentage': (result[4] / total_invoices * 100) if total_invoices > 0 else 0.0
                }
                
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {str(e)}")
            return {
                'avg_confidence': 0.0, 'avg_validation_score': 0.0, 'avg_processing_time': 0.0,
                'success_rate': 0.0, 'high_confidence_percentage': 0.0, 'low_confidence_percentage': 0.0
            }
    
    def _get_financial_insights(self) -> Dict[str, Any]:
        """Generate financial insights and analysis"""
        try:
            # Payment terms analysis
            payment_analysis = self._analyze_payment_terms()
            
            # Amount distribution analysis
            amount_distribution = self._analyze_amount_distribution()
            
            # Currency analysis
            currency_breakdown = self._analyze_currency_distribution()
            
            # Cash flow predictions
            cash_flow_forecast = self._predict_cash_flow()
            
            return {
                'payment_analysis': payment_analysis,
                'amount_distribution': amount_distribution,
                'currency_breakdown': currency_breakdown,
                'cash_flow_forecast': cash_flow_forecast
            }
            
        except Exception as e:
            logger.error(f"Failed to get financial insights: {str(e)}")
            return {}
    
    def _get_alerts_and_anomalies(self) -> Dict[str, Any]:
        """Detect anomalies and generate alerts"""
        try:
            # Detect unusual amounts
            amount_anomalies = self._detect_amount_anomalies()
            
            # Detect processing quality issues
            quality_alerts = self._detect_quality_issues()
            
            # Detect vendor anomalies
            vendor_anomalies = self._detect_vendor_anomalies()
            
            # Compliance alerts
            compliance_alerts = self._check_compliance_issues()
            
            all_alerts = amount_anomalies + quality_alerts + vendor_anomalies + compliance_alerts
            
            return {
                'total_alerts': len(all_alerts),
                'high_priority_alerts': len([a for a in all_alerts if a.get('priority') == 'high']),
                'alerts': all_alerts[:10],  # Top 10 most recent alerts
                'alert_categories': {
                    'amount': len(amount_anomalies),
                    'quality': len(quality_alerts),
                    'vendor': len(vendor_anomalies),
                    'compliance': len(compliance_alerts)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get alerts and anomalies: {str(e)}")
            return {'total_alerts': 0, 'high_priority_alerts': 0, 'alerts': [], 'alert_categories': {}}
    
    def get_monthly_trend(self) -> List[Dict]:
        """Get monthly invoice processing trends"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        strftime('%Y-%m', invoice_date) as month,
                        COUNT(*) as count,
                        SUM(total_amount) as total_amount,
                        AVG(total_amount) as avg_amount
                    FROM invoices 
                    WHERE invoice_date IS NOT NULL 
                    AND invoice_date >= date('now', '-12 months')
                    GROUP BY strftime('%Y-%m', invoice_date)
                    ORDER BY month
                """)
                
                return [
                    {
                        'month': row[0],
                        'count': row[1],
                        'total_amount': row[2] or 0.0,
                        'avg_amount': row[3] or 0.0
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"Failed to get monthly trend: {str(e)}")
            return []
    
    def get_vendor_distribution(self) -> List[Dict]:
        """Get vendor distribution analysis"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        vendor_name,
                        COUNT(*) as count,
                        SUM(total_amount) as total_amount,
                        AVG(total_amount) as avg_amount,
                        MAX(invoice_date) as last_invoice
                    FROM invoices 
                    WHERE vendor_name IS NOT NULL 
                    AND total_amount IS NOT NULL
                    GROUP BY vendor_name 
                    ORDER BY total_amount DESC
                    LIMIT 20
                """)
                
                return [
                    {
                        'vendor': row[0],
                        'count': row[1],
                        'total_amount': row[2] or 0.0,
                        'avg_amount': row[3] or 0.0,
                        'last_invoice': row[4]
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"Failed to get vendor distribution: {str(e)}")
            return []
    
    def _get_monthly_comparison(self) -> Dict[str, int]:
        """Compare current month with previous month"""
        try:
            with self.db_manager._get_connection() as conn:
                # Current month
                cursor = conn.execute("""
                    SELECT COUNT(*), SUM(total_amount)
                    FROM invoices 
                    WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
                """)
                this_month_data = cursor.fetchone()
                
                # Previous month
                cursor = conn.execute("""
                    SELECT COUNT(*), SUM(total_amount)
                    FROM invoices 
                    WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', '-1 month')
                """)
                last_month_data = cursor.fetchone()
                
                this_month_count = this_month_data[0] or 0
                last_month_count = last_month_data[0] or 0
                this_month_amount = this_month_data[1] or 0.0
                last_month_amount = last_month_data[1] or 0.0
                
                return {
                    'this_month': this_month_count,
                    'last_month': last_month_count,
                    'amount_change': this_month_amount - last_month_amount
                }
                
        except Exception as e:
            logger.error(f"Failed to get monthly comparison: {str(e)}")
            return {'this_month': 0, 'last_month': 0, 'amount_change': 0.0}
    
    def _analyze_seasonal_patterns(self) -> Dict[str, Any]:
        """Analyze seasonal patterns in invoice processing"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        strftime('%m', invoice_date) as month,
                        COUNT(*) as count,
                        AVG(total_amount) as avg_amount
                    FROM invoices 
                    WHERE invoice_date IS NOT NULL
                    GROUP BY strftime('%m', invoice_date)
                    ORDER BY month
                """)
                
                monthly_data = cursor.fetchall()
                
                if len(monthly_data) < 12:
                    return {'insufficient_data': True}
                
                counts = [row[1] for row in monthly_data]
                amounts = [row[2] for row in monthly_data]
                
                # Simple seasonality detection
                max_month = counts.index(max(counts)) + 1
                min_month = counts.index(min(counts)) + 1
                
                return {
                    'peak_month': max_month,
                    'lowest_month': min_month,
                    'seasonality_ratio': max(counts) / min(counts) if min(counts) > 0 else 1,
                    'monthly_distribution': {
                        str(i+1): count for i, count in enumerate(counts)
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to analyze seasonal patterns: {str(e)}")
            return {}
    
    def _analyze_vendor_performance(self) -> Dict[str, Any]:
        """Analyze vendor performance metrics"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        vendor_name,
                        COUNT(*) as invoice_count,
                        AVG(confidence) as avg_confidence,
                        AVG(processing_time) as avg_processing_time,
                        SUM(total_amount) as total_spent,
                        AVG(total_amount) as avg_amount
                    FROM invoices 
                    WHERE vendor_name IS NOT NULL
                    GROUP BY vendor_name
                    HAVING COUNT(*) >= 3  -- Only vendors with 3+ invoices
                    ORDER BY total_spent DESC
                """)
                
                vendor_data = cursor.fetchall()
                
                if not vendor_data:
                    return {}
                
                # Calculate performance scores
                performance_metrics = []
                for vendor in vendor_data:
                    performance_score = (
                        (vendor[2] or 0) * 0.4 +  # Confidence weight
                        (1 - min((vendor[3] or 0) / 10, 1)) * 0.3 +  # Processing time weight (inverted)
                        min((vendor[1] / 10), 1) * 0.3  # Volume weight
                    )
                    
                    performance_metrics.append({
                        'vendor': vendor[0],
                        'performance_score': performance_score,
                        'invoice_count': vendor[1],
                        'avg_confidence': vendor[2] or 0,
                        'avg_processing_time': vendor[3] or 0,
                        'total_spent': vendor[4] or 0,
                        'avg_amount': vendor[5] or 0
                    })
                
                # Sort by performance score
                performance_metrics.sort(key=lambda x: x['performance_score'], reverse=True)
                
                return {
                    'top_performers': performance_metrics[:5],
                    'needs_attention': [v for v in performance_metrics if v['performance_score'] < 0.6],
                    'overall_metrics': {
                        'avg_performance_score': np.mean([v['performance_score'] for v in performance_metrics]),
                        'total_vendors_analyzed': len(performance_metrics)
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to analyze vendor performance: {str(e)}")
            return {}
    
    def _calculate_vendor_concentration(self) -> float:
        """Calculate vendor concentration (Herfindahl-Hirschman Index)"""
        try:
            vendor_data = self.get_vendor_distribution()
            
            if not vendor_data:
                return 0.0
            
            total_amount = sum(v['total_amount'] for v in vendor_data)
            
            if total_amount == 0:
                return 0.0
            
            # Calculate market shares and HHI
            hhi = sum((v['total_amount'] / total_amount) ** 2 for v in vendor_data)
            
            return hhi
            
        except Exception as e:
            logger.error(f"Failed to calculate vendor concentration: {str(e)}")
            return 0.0
    
    def _analyze_payment_terms(self) -> Dict[str, Any]:
        """Analyze payment terms and patterns"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        payment_terms,
                        COUNT(*) as count,
                        AVG(total_amount) as avg_amount,
                        AVG(julianday(due_date) - julianday(invoice_date)) as avg_days
                    FROM invoices 
                    WHERE payment_terms IS NOT NULL 
                    AND due_date IS NOT NULL 
                    AND invoice_date IS NOT NULL
                    GROUP BY payment_terms
                    ORDER BY count DESC
                """)
                
                terms_data = cursor.fetchall()
                
                # Calculate average payment period
                cursor = conn.execute("""
                    SELECT AVG(julianday(due_date) - julianday(invoice_date)) as avg_payment_days
                    FROM invoices 
                    WHERE due_date IS NOT NULL AND invoice_date IS NOT NULL
                """)
                
                avg_payment_days = cursor.fetchone()[0] or 0
                
                return {
                    'common_terms': [
                        {
                            'terms': row[0],
                            'count': row[1],
                            'avg_amount': row[2] or 0,
                            'avg_days': row[3] or 0
                        }
                        for row in terms_data[:10]
                    ],
                    'avg_payment_period': avg_payment_days,
                    'payment_distribution': self._categorize_payment_terms(terms_data)
                }
                
        except Exception as e:
            logger.error(f"Failed to analyze payment terms: {str(e)}")
            return {}
    
    def _analyze_amount_distribution(self) -> Dict[str, Any]:
        """Analyze invoice amount distribution"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT total_amount 
                    FROM invoices 
                    WHERE total_amount IS NOT NULL AND total_amount > 0
                """)
                
                amounts = [row[0] for row in cursor.fetchall()]
                
                if not amounts:
                    return {}
                
                amounts_array = np.array(amounts)
                
                # Calculate percentiles and statistics
                percentiles = np.percentile(amounts_array, [25, 50, 75, 90, 95, 99])
                
                # Categorize amounts
                categories = {
                    'small': len([a for a in amounts if a < percentiles[0]]),
                    'medium': len([a for a in amounts if percentiles[0] <= a < percentiles[2]]),
                    'large': len([a for a in amounts if percentiles[2] <= a < percentiles[4]]),
                    'very_large': len([a for a in amounts if a >= percentiles[4]])
                }
                
                return {
                    'total_invoices': len(amounts),
                    'mean': float(np.mean(amounts_array)),
                    'median': float(np.median(amounts_array)),
                    'std_dev': float(np.std(amounts_array)),
                    'percentiles': {
                        '25th': float(percentiles[0]),
                        '50th': float(percentiles[1]),
                        '75th': float(percentiles[2]),
                        '90th': float(percentiles[3]),
                        '95th': float(percentiles[4]),
                        '99th': float(percentiles[5])
                    },
                    'categories': categories
                }
                
        except Exception as e:
            logger.error(f"Failed to analyze amount distribution: {str(e)}")
            return {}
    
    def _analyze_currency_distribution(self) -> Dict[str, Any]:
        """Analyze currency usage patterns"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        currency,
                        COUNT(*) as count,
                        SUM(total_amount) as total_amount,
                        AVG(total_amount) as avg_amount
                    FROM invoices 
                    WHERE currency IS NOT NULL
                    GROUP BY currency
                    ORDER BY count DESC
                """)
                
                currency_data = cursor.fetchall()
                
                total_invoices = sum(row[1] for row in currency_data)
                
                return {
                    'distribution': [
                        {
                            'currency': row[0],
                            'count': row[1],
                            'percentage': (row[1] / total_invoices * 100) if total_invoices > 0 else 0,
                            'total_amount': row[2] or 0,
                            'avg_amount': row[3] or 0
                        }
                        for row in currency_data
                    ],
                    'total_currencies': len(currency_data),
                    'primary_currency': currency_data[0][0] if currency_data else 'USD'
                }
                
        except Exception as e:
            logger.error(f"Failed to analyze currency distribution: {str(e)}")
            return {}
    
    def _predict_cash_flow(self) -> Dict[str, Any]:
        """Predict future cash flow based on historical data"""
        try:
            # Get historical monthly data
            monthly_data = self.get_monthly_trend()
            
            if len(monthly_data) < 6:  # Need at least 6 months for prediction
                return {'insufficient_data': True}
            
            # Prepare data for prediction
            months = list(range(len(monthly_data)))
            amounts = [d['total_amount'] for d in monthly_data]
            
            # Simple linear regression for trend
            X = np.array(months).reshape(-1, 1)
            y = np.array(amounts)
            
            model = LinearRegression()
            model.fit(X, y)
            
            # Predict next 3 months
            future_months = [len(monthly_data) + i for i in range(1, 4)]
            future_X = np.array(future_months).reshape(-1, 1)
            predictions = model.predict(future_X)
            
            # Calculate trend
            trend = 'increasing' if model.coef_[0] > 0 else 'decreasing'
            
            return {
                'predictions': [
                    {
                        'month': f"Month +{i+1}",
                        'predicted_amount': float(pred)
                    }
                    for i, pred in enumerate(predictions)
                ],
                'trend': trend,
                'monthly_growth_rate': float(model.coef_[0]),
                'confidence': 'medium'  # Simple model, medium confidence
            }
            
        except Exception as e:
            logger.error(f"Failed to predict cash flow: {str(e)}")
            return {}
    
    def _detect_amount_anomalies(self) -> List[Dict]:
        """Detect anomalous invoice amounts using statistical methods"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, invoice_number, vendor_name, total_amount, invoice_date
                    FROM invoices 
                    WHERE total_amount IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 100
                """)
                
                recent_invoices = cursor.fetchall()
                
                if len(recent_invoices) < 10:
                    return []
                
                amounts = [row[3] for row in recent_invoices]
                mean_amount = np.mean(amounts)
                std_amount = np.std(amounts)
                
                # Detect outliers using 3-sigma rule
                anomalies = []
                for invoice in recent_invoices:
                    amount = invoice[3]
                    z_score = abs((amount - mean_amount) / std_amount) if std_amount > 0 else 0
                    
                    if z_score > 3:  # More than 3 standard deviations
                        anomalies.append({
                            'type': 'amount_anomaly',
                            'severity': 'high' if z_score > 4 else 'medium',
                            'message': f"Unusual amount: ${amount:,.2f} for invoice {invoice[1]}",
                            'invoice_id': invoice[0],
                            'vendor': invoice[2],
                            'amount': amount,
                            'z_score': z_score,
                            'date': invoice[4]
                        })
                
                return anomalies[:5]  # Return top 5 anomalies
                
        except Exception as e:
            logger.error(f"Failed to detect amount anomalies: {str(e)}")
            return []
    
    def _detect_quality_issues(self) -> List[Dict]:
        """Detect data quality issues in recent processing"""
        try:
            with self.db_manager._get_connection() as conn:
                # Low confidence extractions
                cursor = conn.execute("""
                    SELECT id, invoice_number, vendor_name, confidence, validation_score
                    FROM invoices 
                    WHERE confidence < 0.7 OR validation_score < 0.7
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                
                quality_issues = []
                for row in cursor.fetchall():
                    issue_type = []
                    if row[3] and row[3] < 0.7:
                        issue_type.append(f"Low AI confidence ({row[3]:.1%})")
                    if row[4] and row[4] < 0.7:
                        issue_type.append(f"Low validation score ({row[4]:.1%})")
                    
                    quality_issues.append({
                        'type': 'quality_issue',
                        'severity': 'medium',
                        'message': f"Quality issues: {', '.join(issue_type)}",
                        'invoice_id': row[0],
                        'invoice_number': row[1],
                        'vendor': row[2],
                        'confidence': row[3],
                        'validation_score': row[4]
                    })
                
                return quality_issues
                
        except Exception as e:
            logger.error(f"Failed to detect quality issues: {str(e)}")
            return []
    
    def _detect_vendor_anomalies(self) -> List[Dict]:
        """Detect unusual patterns in vendor behavior"""
        try:
            # Detect new vendors or unusual spending patterns
            with self.db_manager._get_connection() as conn:
                # New vendors (first invoice in last 30 days)
                cursor = conn.execute("""
                    SELECT vendor_name, COUNT(*) as invoice_count, SUM(total_amount) as total_amount
                    FROM invoices 
                    WHERE created_at >= date('now', '-30 days')
                    GROUP BY vendor_name
                    HAVING COUNT(*) = 1  -- Only one invoice (new vendor)
                    ORDER BY total_amount DESC
                """)
                
                anomalies = []
                for row in cursor.fetchall():
                    anomalies.append({
                        'type': 'new_vendor',
                        'severity': 'low',
                        'message': f"New vendor detected: {row[0]} (${row[2]:,.2f})",
                        'vendor': row[0],
                        'amount': row[2]
                    })
                
                return anomalies[:3]  # Return top 3
                
        except Exception as e:
            logger.error(f"Failed to detect vendor anomalies: {str(e)}")
            return []
    
    def _check_compliance_issues(self) -> List[Dict]:
        """Check for potential compliance issues"""
        try:
            compliance_issues = []
            
            # Check for missing required fields
            with self.db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) 
                    FROM invoices 
                    WHERE invoice_number IS NULL OR invoice_number = ''
                    OR vendor_name IS NULL OR vendor_name = ''
                    OR total_amount IS NULL
                """)
                
                missing_fields_count = cursor.fetchone()[0]
                
                if missing_fields_count > 0:
                    compliance_issues.append({
                        'type': 'missing_data',
                        'severity': 'medium',
                        'message': f"{missing_fields_count} invoices with missing required fields",
                        'count': missing_fields_count
                    })
                
                # Check for very old unpaid invoices (assuming due_date tracking)
                cursor = conn.execute("""
                    SELECT COUNT(*) 
                    FROM invoices 
                    WHERE due_date < date('now', '-90 days')
                    AND due_date IS NOT NULL
                """)
                
                overdue_count = cursor.fetchone()[0]
                
                if overdue_count > 0:
                    compliance_issues.append({
                        'type': 'overdue_invoices',
                        'severity': 'high',
                        'message': f"{overdue_count} invoices overdue by more than 90 days",
                        'count': overdue_count
                    })
            
            return compliance_issues
            
        except Exception as e:
            logger.error(f"Failed to check compliance issues: {str(e)}")
            return []
    
    def _categorize_payment_terms(self, terms_data) -> Dict[str, int]:
        """Categorize payment terms into standard buckets"""
        categories = {
            'immediate': 0,      # Due on receipt, immediate
            'net_15': 0,         # 15 days
            'net_30': 0,         # 30 days
            'net_60': 0,         # 60 days
            'net_90_plus': 0,    # 90+ days
            'other': 0           # Non-standard terms
        }
        
        for term_data in terms_data:
            term = term_data[0].lower() if term_data[0] else ''
            count = term_data[1]
            
            if 'immediate' in term or 'receipt' in term or 'due on' in term:
                categories['immediate'] += count
            elif '15' in term or 'net 15' in term:
                categories['net_15'] += count
            elif '30' in term or 'net 30' in term:
                categories['net_30'] += count
            elif '60' in term or 'net 60' in term:
                categories['net_60'] += count
            elif '90' in term or '120' in term or 'net 90' in term:
                categories['net_90_plus'] += count
            else:
                categories['other'] += count
        
        return categories
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if data is cached and still valid"""
        if cache_key not in self._cache:
            return False
        
        if cache_key not in self._cache_expiry:
            return False
        
        return datetime.now() < self._cache_expiry[cache_key]
    
    def _get_fallback_dashboard_data(self) -> Dict[str, Any]:
        """Return basic fallback data if main analytics fail"""
        return {
            'total_invoices': self.db_manager.get_total_invoices(),
            'total_amount': 0.0,
            'average_amount': 0.0,
            'unique_vendors': 0,
            'invoices_this_month': 0,
            'invoices_last_month': 0,
            'amount_change': 0.0,
            'avg_confidence': 0.0,
            'success_rate': 0.0,
            'monthly_trends': [],
            'vendor_distribution': [],
            'total_alerts': 0,
            'alerts': []
        }
    
    def generate_insights_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive insights report with actionable recommendations
        
        This provides strategic insights that can drive business decisions.
        """
        try:
            dashboard_data = self.get_dashboard_data()
            
            insights = {
                'executive_summary': self._generate_executive_summary(dashboard_data),
                'cost_optimization': self._analyze_cost_optimization(dashboard_data),
                'vendor_recommendations': self._generate_vendor_recommendations(dashboard_data),
                'process_improvements': self._suggest_process_improvements(dashboard_data),
                'risk_assessment': self._assess_risks(dashboard_data),
                'action_items': self._generate_action_items(dashboard_data)
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate insights report: {str(e)}")
            return {}
    
    def _generate_executive_summary(self, dashboard_data: Dict) -> str:
        """Generate executive summary of invoice processing performance"""
        total_invoices = dashboard_data.get('total_invoices', 0)
        total_amount = dashboard_data.get('total_amount', 0)
        growth_rate = dashboard_data.get('growth_rate', 0)
        
        summary = f"""
        Invoice Processing Summary:
        • Processed {total_invoices:,} invoices totaling ${total_amount:,.2f}
        • Month-over-month growth: {growth_rate:+.1f}%
        • AI processing success rate: {dashboard_data.get('success_rate', 0):.1%}
        • Average processing time: {dashboard_data.get('avg_processing_time', 0):.1f} seconds
        """
        
        return summary.strip()
    
    def _analyze_cost_optimization(self, dashboard_data: Dict) -> List[str]:
        """Analyze opportunities for cost optimization"""
        recommendations = []
        
        vendor_concentration = dashboard_data.get('vendor_concentration', 0)
        if vendor_concentration > 0.3:
            recommendations.append("High vendor concentration detected - consider diversifying suppliers")
        
        payment_analysis = dashboard_data.get('payment_analysis', {})
        avg_payment_days = payment_analysis.get('avg_payment_period', 0)
        if avg_payment_days < 30:
            recommendations.append("Short payment terms - negotiate longer terms for better cash flow")
        
        return recommendations
    
    def _generate_vendor_recommendations(self, dashboard_data: Dict) -> List[str]:
        """Generate vendor-specific recommendations"""
        recommendations = []
        
        vendor_performance = dashboard_data.get('vendor_performance', {})
        needs_attention = vendor_performance.get('needs_attention', [])
        
        if needs_attention:
            recommendations.append(f"Review {len(needs_attention)} vendors with low performance scores")
        
        return recommendations
    
    def _suggest_process_improvements(self, dashboard_data: Dict) -> List[str]:
        """Suggest process improvements based on data"""
        suggestions = []
        
        avg_confidence = dashboard_data.get('avg_confidence', 0)
        if avg_confidence < 0.8:
            suggestions.append("Consider improving document quality to increase AI confidence")
        
        high_priority_alerts = dashboard_data.get('high_priority_alerts', 0)
        if high_priority_alerts > 5:
            suggestions.append("High number of alerts - review processing workflows")
        
        return suggestions
    
    def _assess_risks(self, dashboard_data: Dict) -> List[str]:
        """Assess potential risks based on invoice data patterns"""
        risks = []
        
        alerts = dashboard_data.get('alerts', [])
        amount_anomalies = [a for a in alerts if a.get('type') == 'amount_anomaly']
        
        if len(amount_anomalies) > 3:
            risks.append("Multiple amount anomalies detected - review for potential fraud")
        
        return risks
    
    def _generate_action_items(self, dashboard_data: Dict) -> List[Dict]:
        """Generate specific action items with priorities"""
        actions = []
        
        # High priority actions based on alerts
        high_priority_alerts = dashboard_data.get('high_priority_alerts', 0)
        if high_priority_alerts > 0:
            actions.append({
                'priority': 'high',
                'action': f"Review {high_priority_alerts} high-priority alerts",
                'deadline': 'immediate'
            })
        
        # Medium priority actions
        low_confidence_invoices = dashboard_data.get('low_confidence_percentage', 0)
        if low_confidence_invoices > 20:
            actions.append({
                'priority': 'medium',
                'action': 'Improve document quality training',
                'deadline': 'this_week'
            })
        
        return actions
    
    def clear_cache(self):
        """Clear analytics cache to force fresh calculations"""
        self._cache.clear()
        self._cache_expiry.clear()
        logger.info("Analytics cache cleared")